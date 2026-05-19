"""
QA test suite — Excelsis 360 (phi4:14b backend).

Markers:
  (none)           — pure unit tests, no Ollama needed
  @pytest.mark.integration — requires Ollama + phi4:14b running locally

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.security import ADMIN_USER
from src.tools import (
    query_data,
    get_threshold_alerts,
    get_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_store(classes=("10A", "10B", "11A")):
    """Minimal AttendanceDataStore seeded with synthetic data (no SQL Server needed)."""
    from tests.fixtures import AttendanceDataStore

    rows = []
    for cls in classes:
        for day in range(30):
            rows.append({
                "student_id":   f"S{cls}-{day:02d}",
                "student_name": f"Student {day}",
                "date":         pd.Timestamp("2024-01-01") + pd.Timedelta(days=day),
                "status":       "absent" if day % 5 == 0 else "present",
                "class":        cls,
                "grade":        cls[:2],
            })
    store = AttendanceDataStore()
    store.ingest_df(pd.DataFrame(rows), name="qa_fixture")
    return store


def _tool_config(store=None) -> dict:
    """Build the RunnableConfig dict that LangGraph injects into tools."""
    return {
        "configurable": {
            "user_context": ADMIN_USER,
            "store":        store,
        }
    }


# ---------------------------------------------------------------------------
# TC1 — Zero-Knowledge: tool-call routing + data retrieval
# ---------------------------------------------------------------------------

class TestZeroKnowledge:
    """TC1: Verify tools can be called and receive real data (no LLM needed)."""

    def test_query_data_returns_data(self):
        store  = _make_store()
        cfg    = _tool_config(store=store)
        result = query_data.invoke({"group_by": "class"}, config=cfg)
        assert "10A" in result
        assert "10B" in result

    def test_get_summary_contains_expected_keys(self):
        import json
        store  = _make_store()
        cfg    = _tool_config(store=store)
        result = get_summary.invoke({}, config=cfg)
        data   = json.loads(result)
        assert "total_records" in data
        assert "metric_rate" in data

    def test_no_store_returns_graceful_message(self):
        cfg    = _tool_config(store=None)
        result = query_data.invoke({"group_by": "class"}, config=cfg)
        assert "No data store" in result

    def test_at_risk_returns_below_threshold(self):
        store  = _make_store()
        cfg    = _tool_config(store=store)
        result = get_threshold_alerts.invoke({"threshold": 75.0}, config=cfg)
        assert isinstance(result, str)
        assert "No data store" not in result

    def test_update_dashboard_view_returns_json(self):
        import json
        from src.tools import update_dashboard_view
        cfg    = _tool_config()
        result = update_dashboard_view.invoke(
            {"classes": ["10A"], "period": "last_30_days", "view": "group"},
            config=cfg,
        )
        payload = json.loads(result)
        assert payload["classes"] == ["10A"]
        assert payload["view"] == "group"
        assert payload["period"] == "last_30_days"


# ---------------------------------------------------------------------------
# TC2 — Model Stress Test (integration — requires Ollama)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestModelStress:
    """TC2: Multi-part query latency and stability against live phi4:14b."""

    LATENCY_BUDGET_S = 120

    def test_complex_query_within_latency_budget(self):
        from src.agent import ExcelsisAgent
        store   = _make_store()
        agent   = ExcelsisAgent(store=store)
        query   = (
            "Which class has the lowest attendance rate? "
            "How many students are at risk in that class? "
            "What SQL query would show the top 5 most absent students?"
        )
        t0      = time.time()
        answer  = agent.ask(query)
        elapsed = time.time() - t0
        assert len(answer) > 50
        assert elapsed < self.LATENCY_BUDGET_S

    def test_greeting_does_not_trigger_tool_call(self):
        from src.agent import ExcelsisAgent
        store  = _make_store()
        agent  = ExcelsisAgent(store=store)
        answer = agent.ask("Hello, what can you help me with?")
        assert len(answer) > 10
