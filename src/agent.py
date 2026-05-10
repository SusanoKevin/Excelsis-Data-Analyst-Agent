"""
LangGraph ReAct agent for Excelsis 360.

Two models are used:
- Analysis model (qwen2.5-coder:7b): drives the ReAct loop with tool calling
- Chat model (llama3.1:8b): lightweight conversational replies without tools

Usage
-----
    from src.agent import ExcelsisAgent
    from src.security import UserContext, Role

    agent = ExcelsisAgent(store=store, vector_store=vec)
    answer = agent.ask("Which classes are at risk?", user=UserContext("alice", Role.TEACHER, ["10A"]))
    reply  = agent.chat("Thanks, that was helpful!")
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .security import ADMIN_USER, UserContext
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an expert School Attendance Analyst for Excelsis 360.

Your job is to help school administrators understand attendance patterns and take action.

Guidelines:
- Always flag any class or student below 75% as "at-risk"
- Be specific: name classes and students when data is available
- When recommending interventions, cite research or best practices from the knowledge base
- If you cannot find data, say so clearly — do not make up statistics
- Think step-by-step: first understand what data is needed, then retrieve it, then analyse

You have access to:
- query_attendance     : attendance statistics by class/week/month/student/grade
- get_at_risk_students : list students below a given attendance threshold
- search_knowledge_base: semantic search over policies and class summaries
- get_summary          : high-level attendance overview
- web_search           : external research and best practices
"""


def _make_llm(model: str, temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        temperature=temperature,
    )


class ExcelsisAgent:
    def __init__(
        self,
        store=None,
        vector_store=None,
        analysis_model: Optional[str] = None,
        chat_model: Optional[str] = None,
        max_history: int = 10,
    ) -> None:
        analysis_model = analysis_model or os.environ.get(
            "ANALYSIS_MODEL", "qwen2.5-coder:7b"
        )
        chat_model = chat_model or os.environ.get(
            "CHAT_MODEL", "llama3.1:8b"
        )

        analysis_llm = _make_llm(analysis_model, temperature=0.1)
        self._chat_llm = _make_llm(chat_model, temperature=0.3)

        self._graph = create_react_agent(
            model=analysis_llm,
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        self._store = store
        self._vector_store = vector_store
        self._history: list = []
        self._max_history = max_history

    def ask(self, query: str, user: Optional[UserContext] = None) -> str:
        """Run the ReAct analysis agent (qwen2.5-coder) with tool access."""
        user = user or ADMIN_USER
        config = {
            "configurable": {
                "user_context":  user,
                "store":         self._store,
                "vector_store":  self._vector_store,
            }
        }

        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=query)]

        result = self._graph.invoke({"messages": messages}, config=config)

        final_msg = result["messages"][-1]
        answer = final_msg.content if isinstance(final_msg, AIMessage) else str(final_msg)

        self._history.append(HumanMessage(content=query))
        self._history.append(AIMessage(content=answer))
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2):]

        return answer

    def chat(self, message: str) -> str:
        """Send a plain conversational message to the chat model (llama3.1) without tools."""
        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=message)]
        response = self._chat_llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)

        self._history.append(HumanMessage(content=message))
        self._history.append(AIMessage(content=answer))
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2):]

        return answer

    def reset_history(self) -> None:
        self._history.clear()
