"""
LangGraph ReAct agent for Excelsis 360.

Two models are used:
- Analysis model (Qwen/Qwen2.5-3B-Instruct): drives the ReAct loop with tool calling
- Chat model (google/gemma-2-2b-it): lightweight conversational replies without tools

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
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
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


def _make_endpoint(repo_id: str, max_new_tokens: int = 2048, temperature: float = 0.1) -> ChatHuggingFace:
    endpoint = HuggingFaceEndpoint(
        repo_id=repo_id,
        huggingfacehub_api_token=os.environ.get("HF_TOKEN"),
        task="text-generation",
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        do_sample=True,
    )
    return ChatHuggingFace(llm=endpoint)


class ExcelsisAgent:
    def __init__(
        self,
        store=None,
        vector_store=None,
        analysis_model: Optional[str] = None,
        chat_model: Optional[str] = None,
        max_history: int = 10,
    ) -> None:
        analysis_repo = analysis_model or os.environ.get(
            "ANALYSIS_MODEL", "Qwen/Qwen2.5-3B-Instruct"
        )
        chat_repo = chat_model or os.environ.get(
            "CHAT_MODEL", "google/gemma-2-2b-it"
        )

        analysis_llm = _make_endpoint(analysis_repo, max_new_tokens=2048, temperature=0.1)
        self._chat_llm = _make_endpoint(chat_repo, max_new_tokens=1024, temperature=0.3)

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
        """Run the ReAct analysis agent (Qwen) with tool access."""
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
        """Send a plain conversational message to the chat model (Gemma) without tools."""
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
