"""
LangGraph ReAct agent for Excelsis 360.

The agent replaces the keyword-routing approach in the notebook with a
true reasoning loop: it decides which tools to call, in what order, and
synthesises a final answer — all within the user's security context.

Usage
-----
    from src.agent import ExcelsisAgent
    from src.security import UserContext, Role

    agent = ExcelsisAgent(store=store, vector_store=vec)
    answer = agent.ask("Which classes are at risk?", user=UserContext("alice", Role.TEACHER, ["10A"]))
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
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


class ExcelsisAgent:
    def __init__(
        self,
        store=None,
        vector_store=None,
        model_name: Optional[str] = None,
        max_history: int = 10,
    ) -> None:
        mn = model_name or os.environ.get("LLM_MODEL", "meta/llama-3.1-8b-instruct")
        llm = ChatNVIDIA(
            model=mn,
            api_key=os.environ.get("NVIDIA_API_KEY"),
            base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            temperature=0.1,
            max_tokens=2048,
        )
        self._graph = create_react_agent(
            model=llm,
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        self._store = store
        self._vector_store = vector_store
        self._history: list = []
        self._max_history = max_history

    def ask(self, query: str, user: Optional[UserContext] = None) -> str:
        """
        Run the agent with a natural-language query.

        Parameters
        ----------
        query : str
            The analyst question.
        user : UserContext
            Who is asking. Defaults to ADMIN_USER if omitted.
        """
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

        # Last message is the final AI answer
        final_msg = result["messages"][-1]
        answer = final_msg.content if isinstance(final_msg, AIMessage) else str(final_msg)

        # Update rolling history
        self._history.append(HumanMessage(content=query))
        self._history.append(AIMessage(content=answer))
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2):]

        return answer

    def reset_history(self) -> None:
        self._history.clear()
