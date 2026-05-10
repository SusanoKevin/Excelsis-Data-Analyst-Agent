"""
Two-model pipeline for Excelsis 360.

Request flow:
  User → LLaMA (classifier) → answer directly (streaming)
                             → Qwen ReAct analyst (streaming) → text + optional dashboard
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .security import ADMIN_USER, UserContext
from .tools import ALL_TOOLS

# --------------------------------------------------------------------------- #
# Prompts                                                                      #
# --------------------------------------------------------------------------- #

CLASSIFIER_PROMPT = """You are a query router for the Excelsis 360 school attendance system.

Decide whether the query needs live attendance database data.

Route to the data analyst for:
- Attendance figures, rates, trends, or statistics from the database
- At-risk student identification or class comparisons
- Requests for charts, dashboards, or visualisations
- Questions about specific classes, grades, or students

Answer directly for:
- Greetings, thanks, or small talk
- Conceptual questions ("what does at-risk mean?")
- General advice not requiring live data
- Follow-ups that don't need new data

Respond with ONLY one JSON object, nothing else:
{"action": "answer"}
or
{"action": "route"}"""

CHAT_PROMPT = """You are the Excelsis 360 school attendance assistant.
Answer the user's question helpfully and concisely.
You do not have access to live attendance data — the system routes data queries to the analyst automatically.
Keep responses brief and friendly."""

ANALYST_PROMPT = """You are an expert School Attendance Analyst for Excelsis 360.

Guidelines:
- Always flag any class or student below 75% as "at-risk"
- Be specific: name classes and students when data is available
- When recommending interventions, cite best practices from the knowledge base
- If you cannot find data, say so clearly — do not make up statistics
- Think step-by-step: understand what data is needed, retrieve it, then analyse
- When your answer would benefit from a visual, call generate_dashboard

Available tools:
- query_attendance      : attendance statistics by class/week/month/student/grade
- get_at_risk_students  : list students below a given attendance threshold
- search_knowledge_base : semantic search over policies and class summaries
- get_summary           : high-level attendance overview
- web_search            : external research and best practices
- generate_dashboard    : create a query-specific chart and return its URL"""


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _make_llm(model: str, temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        temperature=temperature,
    )


def _parse_action(text: str) -> str:
    """Return 'answer' or 'route' from the classifier's JSON response."""
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    match = re.search(r"\{[^}]*\}", text)
    if match:
        try:
            return json.loads(match.group()).get("action", "route")
        except json.JSONDecodeError:
            pass
    # Heuristic fallback
    if "answer" in text.lower() and "route" not in text.lower():
        return "answer"
    return "route"


# --------------------------------------------------------------------------- #
# Agent                                                                        #
# --------------------------------------------------------------------------- #

class ExcelsisAgent:
    def __init__(
        self,
        store=None,
        vector_store=None,
        analysis_model: Optional[str] = None,
        chat_model: Optional[str] = None,
        max_history: int = 10,
    ) -> None:
        analysis_model = analysis_model or os.environ.get("ANALYSIS_MODEL", "qwen2.5-coder:7b")
        chat_model     = chat_model     or os.environ.get("CHAT_MODEL",     "llama3.1:8b")

        # LLaMA: classifier (deterministic) + conversationalist (creative)
        self._classifier_llm = _make_llm(chat_model, temperature=0.0)
        self._chat_llm       = _make_llm(chat_model, temperature=0.4)

        # Qwen: ReAct analyst with tools
        self._graph = create_react_agent(
            model=_make_llm(analysis_model, temperature=0.1),
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=ANALYST_PROMPT),
        )

        self._store        = store
        self._vector_store = vector_store
        self._history: list = []
        self._max_history   = max_history

    # --- Internal helpers ---

    def _build_config(self, user: UserContext) -> dict:
        return {
            "configurable": {
                "user_context": user,
                "store":        self._store,
                "vector_store": self._vector_store,
            }
        }

    def _append_history(self, human: str, ai: str) -> None:
        self._history.append(HumanMessage(content=human))
        self._history.append(AIMessage(content=ai))
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2):]

    def _classify(self, message: str) -> str:
        """Ask LLaMA to classify the query. Returns 'answer' or 'route'."""
        msgs = [
            SystemMessage(content=CLASSIFIER_PROMPT),
            *self._history[-4:],          # small context for fast classification
            HumanMessage(content=message),
        ]
        return _parse_action(self._classifier_llm.invoke(msgs).content)

    # --- Synchronous API (notebook / MCP) ---

    def ask(self, query: str, user: Optional[UserContext] = None) -> str:
        """Route query through LLaMA classifier, then answer or delegate to Qwen."""
        user   = user or ADMIN_USER
        action = self._classify(query)

        if action == "answer":
            msgs = [
                SystemMessage(content=CHAT_PROMPT),
                *self._history[-self._max_history:],
                HumanMessage(content=query),
            ]
            response = self._chat_llm.invoke(msgs)
            answer   = response.content if hasattr(response, "content") else str(response)
            self._append_history(query, answer)
            return answer

        config   = self._build_config(user)
        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=query)]
        result   = self._graph.invoke({"messages": messages}, config=config)
        final    = result["messages"][-1]
        answer   = final.content if isinstance(final, AIMessage) else str(final)
        self._append_history(query, answer)
        return answer

    def chat(self, message: str) -> str:
        return self.ask(message)

    # --- Async streaming API (/chat/stream SSE) ---

    async def astream_events(self, message: str, user: Optional[UserContext] = None):
        """
        Async generator yielding SSE-ready dicts.

        Event types emitted:
          {"type": "routing"}                             LLaMA routed to Qwen analyst
          {"type": "token",     "content": "..."}         text token (from either model)
          {"type": "tool_start","tool":    "..."}         Qwen calling a tool
          {"type": "tool_end",  "tool":    "..."}         tool finished
          {"type": "dashboard", "url":     "/dashboards/…"} dashboard PNG ready
        """
        user   = user or ADMIN_USER
        action = self._classify(message)

        if action == "answer":
            msgs = [
                SystemMessage(content=CHAT_PROMPT),
                *self._history[-self._max_history:],
                HumanMessage(content=message),
            ]
            full = ""
            async for chunk in self._chat_llm.astream(msgs):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    full += token
                    yield {"type": "token", "content": token}
            self._append_history(message, full)
            return

        yield {"type": "routing"}

        config   = self._build_config(user)
        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=message)]
        full     = ""

        async for event in self._graph.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full += chunk.content
                    yield {"type": "token", "content": chunk.content}

            elif kind == "on_tool_start":
                yield {"type": "tool_start", "tool": event.get("name", "")}

            elif kind == "on_tool_end":
                name = event.get("name", "")
                yield {"type": "tool_end", "tool": name}
                if name == "generate_dashboard":
                    output = event.get("data", {}).get("output", "")
                    if output and output.startswith("/dashboards/"):
                        yield {"type": "dashboard", "url": output}

        self._append_history(message, full)

    def reset_history(self) -> None:
        self._history.clear()
