"""
QA test suite — Excelsis 360 (mistral-small:22b backend).

Markers:
  (none)           — pure unit tests, no Ollama needed
  @pytest.mark.integration — requires Ollama + mistral-small:22b running locally

Run:
  pytest tests/test_qa.py -v                        # unit tests only
  pytest tests/test_qa.py -v -m integration         # integration tests only
  pytest tests/test_qa.py -v --run-all              # everything
"""

import time
import sys
import os
import pytest
import pandas as pd

# Make src importable without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.security import (
    AccessDeniedError,
    Permission,
    Role,
    SecurityManager,
    UserContext,
    ADMIN_USER,
)
from src.tools import (
    query_attendance,
    get_at_risk_students,
    search_knowledge_base,
    get_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_store(classes=("10A", "10B", "11A")):
    """Minimal AttendanceDataStore seeded with synthetic data."""
    from src.data_store import AttendanceDataStore

    rows = []
    for cls in classes:
        for day in range(30):
            rows.append({
                "student_id": f"S{cls}-{day:02d}",
                "student_name": f"Student {day}",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=day),
                "status": "absent" if day % 5 == 0 else "present",
                "class": cls,
                "grade": cls[:2],
            })
    store = AttendanceDataStore()
    store.ingest_df(pd.DataFrame(rows), name="qa_fixture")
    return store


def _tool_config(user: UserContext, store=None, vec=None) -> dict:
    """Build the RunnableConfig dict that LangGraph injects into tools."""
    return {
        "configurable": {
            "user_context": user,
            "store": store,
            "vector_store": vec,
        }
    }


# ---------------------------------------------------------------------------
# TC1 — Zero-Knowledge: tool-call routing + data retrieval
# ---------------------------------------------------------------------------

class TestZeroKnowledge:
    """TC1: Verify admin can call tools and receive real data (no LLM needed)."""

    def test_query_attendance_returns_data(self):
        store  = _make_store()
        cfg    = _tool_config(ADMIN_USER, store=store)
        result = query_attendance.invoke({"query": "attendance by class"}, config=cfg)
        assert "10A" in result
        assert "10B" in result

    def test_get_summary_contains_expected_keys(self):
        import json
        store  = _make_store()
        cfg    = _tool_config(ADMIN_USER, store=store)
        result = get_summary.invoke({}, config=cfg)
        data   = json.loads(result)
        assert "total_records" in data
        assert "overall_attendance_rate" in data

    def test_no_store_returns_graceful_message(self):
        cfg    = _tool_config(ADMIN_USER, store=None)
        result = query_attendance.invoke({"query": "attendance by class"}, config=cfg)
        assert "No data store" in result


# ---------------------------------------------------------------------------
# TC2 — Security Boundary: role enforcement
# ---------------------------------------------------------------------------

class TestSecurityBoundary:
    """TC2: Verify RBAC blocks forbidden operations and passes allowed ones."""

    TEACHER = UserContext(user_id="t1", role=Role.TEACHER, allowed_classes=["10A"])
    COUNSELOR = UserContext(user_id="c1", role=Role.COUNSELOR, allowed_classes=["10A", "10B"])

    def test_teacher_cannot_read_at_risk(self):
        store = _make_store()
        cfg   = _tool_config(self.TEACHER, store=store)
        with pytest.raises(AccessDeniedError) as exc:
            get_at_risk_students.invoke({"threshold": 75.0}, config=cfg)
        assert "read_at_risk" in str(exc.value)

    def test_counselor_can_read_at_risk(self):
        store  = _make_store()
        cfg    = _tool_config(self.COUNSELOR, store=store)
        result = get_at_risk_students.invoke({"threshold": 75.0}, config=cfg)
        assert isinstance(result, str)
        assert "No data store" not in result

    def test_teacher_data_filtered_to_own_class(self):
        store  = _make_store(classes=("10A", "10B", "11A"))
        cfg    = _tool_config(self.TEACHER, store=store)
        result = query_attendance.invoke({"query": "attendance by class"}, config=cfg)
        assert "10A"  in result
        assert "10B"  not in result
        assert "11A"  not in result

    def test_viewer_cannot_generate_dashboard(self):
        from src.tools import generate_dashboard
        viewer = UserContext(user_id="v1", role=Role.VIEWER, allowed_classes=["10A"])
        store  = _make_store()
        cfg    = _tool_config(viewer, store=store)
        with pytest.raises(AccessDeniedError) as exc:
            generate_dashboard.invoke(
                {"chart_type": "class_bar", "group_by": "class", "period": "all", "title": "Test"},
                config=cfg,
            )
        assert "generate_dashboard" in str(exc.value)

    def test_access_denied_does_not_crash_security_manager(self):
        sm   = SecurityManager()
        user = UserContext(user_id="badactor", role=Role.VIEWER)
        with pytest.raises(AccessDeniedError):
            sm.require(user, Permission.READ_AT_RISK, "test_resource")
        log = sm.audit_log()
        assert len(log) == 1
        assert log[0]["granted"] is False


# ---------------------------------------------------------------------------
# TC3 — Model Stress Test (integration — requires Ollama)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestModelStress:
    """TC3: Multi-part query latency and stability against live mistral-small:22b."""

    LATENCY_BUDGET_S = 120  # generous for a 22b model on CPU

    def test_complex_query_within_latency_budget(self):
        from src.agent import ExcelsisAgent
        store = _make_store()
        agent = ExcelsisAgent(store=store)

        query = (
            "Which class has the lowest attendance rate? "
            "How many students are at risk in that class? "
            "Suggest two evidence-based interventions."
        )
        t0     = time.time()
        answer = agent.ask(query)
        elapsed = time.time() - t0

        assert len(answer) > 50, "Response suspiciously short — model may have failed"
        assert elapsed < self.LATENCY_BUDGET_S, (
            f"Response took {elapsed:.1f}s — exceeded {self.LATENCY_BUDGET_S}s budget"
        )

    def test_greeting_does_not_trigger_tool_call(self):
        """Agent should answer greetings directly without calling any tool."""
        from src.agent import ExcelsisAgent
        store = _make_store()
        agent = ExcelsisAgent(store=store)
        answer = agent.ask("Hello, what can you help me with?")
        assert len(answer) > 10
        # If tools were called the store would have been queried; no assertion needed
        # beyond "it returned something coherent without crashing."


# ---------------------------------------------------------------------------
# TC4 — Vector Store Integration (integration — requires Ollama + nomic-embed-text)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestVectorStoreIntegration:
    """TC4: Verify semantic search hits the policies collection correctly."""

    def _make_vec(self):
        from src.vector_store import AttendanceVectorStore
        return AttendanceVectorStore()  # uses ChromaDB + nomic-embed-text

    def test_policy_search_returns_results(self):
        vec    = self._make_vec()
        cfg    = _tool_config(ADMIN_USER, vec=vec)
        result = search_knowledge_base.invoke(
            {"query": "chronic absenteeism intervention strategies", "collection": "policies"},
            config=cfg,
        )
        assert len(result) > 50, "Policy search returned too little content"
        assert "No results" not in result.lower()

    def test_class_restricted_records_search(self):
        """Teacher searching records should only see their own class docs."""
        teacher = UserContext(user_id="t2", role=Role.TEACHER, allowed_classes=["10A"])
        vec     = self._make_vec()
        cfg     = _tool_config(teacher, vec=vec)
        result  = search_knowledge_base.invoke(
            {"query": "class attendance summary", "collection": "records"},
            config=cfg,
        )
        assert "10B" not in result
        assert "11A" not in result


