"""
Excelsis 360 agent — unified Ollama ReAct pipeline.

Request flow:
  User → mistral-small:22b (native tool calling) → tools → text + optional dashboard
"""

from __future__ import annotations

import ast
import json
import os
import re
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .security import ADMIN_USER, UserContext
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an expert School Attendance Analyst for Excelsis 360.

Guidelines:
- Always flag any class or student below 75% as "at-risk"
- Be specific: name classes and students when data is available
- If you cannot find data, say so clearly — never fabricate statistics or URLs
- Think step-by-step: retrieve data first, then analyse
- For greetings or general questions, answer directly without calling tools
- If the user asks for a chart, dashboard, or visual: you MUST call generate_dashboard — never invent a URL

Tool usage:
- query_attendance      — attendance statistics
- get_at_risk_students  — students below a threshold
- generate_dashboard    — chart or visual requests; always pass a descriptive title
- search_knowledge_base — policy and intervention advice
- get_summary           — quick data overview

Dashboard rules (generate_dashboard):
- Choose the single most relevant chart_type for the question:
    class_bar    → "which classes have lowest attendance?"
    weekly_trend → "show trends over time / weekly attendance"
    weekday_bar  → "which day has most absences?"
    status_donut → "breakdown of present / absent / late"
    at_risk_bar  → "show at-risk students"
    grade_bar    → "attendance by grade"
    full         → ONLY for "show me everything" / "full dashboard" / "overview"
- Pass period='last_30_days' for recent-data questions, 'all' for historical ones.

CRITICAL: Call tools immediately — NEVER output text like "I will use X tool" or
"Let me call X" before calling it. Narrating a tool call instead of making one is
an error.
"""


class _OllamaWithToolParsing(ChatOllama):
    """ChatOllama wrapper that converts mistral-small's text tool-call JSON
    into structured tool_calls so LangGraph can execute them."""

    # Format 2: await functions.tool_name({"key": "val"})
    _PYFUNC_RE = re.compile(
        r'(?:response\s*=\s*)?(?:await\s+)?functions\.(\w+)\((\{.*?\})\)',
        re.DOTALL,
    )
    # Format 3 / 4: bare_name({...}) or code-block {"code": "name({...})"}
    _BARE_RE = re.compile(r'^(\w+)\((\{.*\})\)\s*$', re.DOTALL)

    # Format 7: "I will use `tool_name` tool" narration without an actual tool call
    _TOOL_NAMES = frozenset({
        "query_attendance", "get_at_risk_students", "search_knowledge_base",
        "get_summary", "generate_dashboard",
    })
    # Extracts the intent/query from two common announcement patterns
    _INTENT_RE = re.compile(
        r'[Tt]o (?:provide you with )?(.+?),\s*[Ii](?:\s+will)?\s+(?:use|call)|'
        r'to (?:retrieve|find|get|search for)\s+(.+?)(?:[.,]|$)'
    )

    @staticmethod
    def _parse_json_tool_calls(data) -> list[dict] | None:
        """Convert parsed JSON (list or dict) to tool_calls if it looks like tool calls."""
        if isinstance(data, list) and data and "name" in data[0]:
            return [{"name": tc["name"], "args": tc.get("arguments", {}),
                     "id": f"call_{i}", "type": "tool_call"}
                    for i, tc in enumerate(data)]
        if isinstance(data, dict) and "name" in data:
            return [{"name": data["name"], "args": data.get("arguments", {}),
                     "id": "call_0", "type": "tool_call"}]
        return None

    def _fix(self, msg: AIMessage) -> AIMessage:
        if msg.tool_calls or not msg.content:
            return msg
        content = msg.content.strip()

        # Try raw JSON first (Format 1: array, or single-object variant)
        try:
            calls = self._parse_json_tool_calls(json.loads(content))
            if calls:
                return AIMessage(content="", tool_calls=calls)
        except Exception:
            pass

        # Format 2: await functions.tool_name({...})
        matches = self._PYFUNC_RE.findall(content)
        if matches:
            tool_calls = []
            for i, (name, args_str) in enumerate(matches):
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                tool_calls.append(
                    {"name": name, "args": args, "id": f"call_{i}", "type": "tool_call"}
                )
            return AIMessage(content="", tool_calls=tool_calls)

        # Strip any markdown code-block wrapper and retry JSON / function-call formats
        inner = re.sub(r'^```\w*\s*|\s*```$', '', content, flags=re.DOTALL).strip()
        if inner != content:
            # Retry JSON (handles ```{"name":...}``` and ```[{"name":...}]```)
            try:
                calls = self._parse_json_tool_calls(json.loads(inner))
                if calls:
                    return AIMessage(content="", tool_calls=calls)
            except Exception:
                pass
            # {"code": "name({...})"} wrapper
            try:
                data = json.loads(inner)
                if isinstance(data, dict) and "code" in data:
                    inner = data["code"].strip()
            except Exception:
                pass

        # Format 4 / 5: Python function call — name({...}) or name(key=val, ...)
        # ast.parse handles both positional-dict and keyword-argument styles
        try:
            tree = ast.parse(inner, mode="eval")
            call = tree.body
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                name = call.func.id
                if call.args and not call.keywords:
                    args = ast.literal_eval(call.args[0])
                elif call.keywords and not call.args:
                    args = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
                else:
                    args = {}
                if isinstance(args, dict):
                    return AIMessage(content="", tool_calls=[
                        {"name": name, "args": args, "id": "call_0", "type": "tool_call"}
                    ])
        except Exception:
            pass

        # Format 6: JSON tool call embedded at the end of mixed text
        # e.g. "Some reasoning...\n[{"name":"tool","arguments":{}}]"
        for line in reversed(content.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                calls = self._parse_json_tool_calls(json.loads(line))
                if calls:
                    return AIMessage(content="", tool_calls=calls)
            except Exception:
                pass
            break  # only check the last non-empty line

        # Format 7: model narrated "I will use `tool_name` tool" instead of calling it
        for m in re.finditer(r'`(\w+)`', content):
            name = m.group(1)
            if name not in self._TOOL_NAMES:
                continue
            qm = self._INTENT_RE.search(content)
            query = next((g for g in (qm.groups() if qm else ()) if g), content)
            args = {"query": query.strip()} if name in ("query_attendance", "search_knowledge_base") else {}
            return AIMessage(content="", tool_calls=[
                {"name": name, "args": args, "id": "call_0", "type": "tool_call"}
            ])

        return msg

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        gens = [ChatGeneration(message=self._fix(g.message), text="")
                for g in result.generations]
        return ChatResult(generations=gens, llm_output=result.llm_output)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        result = await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        gens = [ChatGeneration(message=self._fix(g.message), text="")
                for g in result.generations]
        return ChatResult(generations=gens, llm_output=result.llm_output)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        # Buffer all chunks so _fix can inspect the complete output before routing.
        # LangGraph calls _astream (not _agenerate) for astream_events, so without
        # this override tool-call JSON text is never converted to tool_calls and
        # should_continue always returns END.
        from langchain_core.messages import AIMessage, AIMessageChunk
        from langchain_core.outputs import ChatGenerationChunk
        chunks = []
        async for chunk in super()._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
            chunks.append(chunk)
        if not chunks:
            return
        # ChatOllama._astream yields ChatGenerationChunk; .message is the AIMessageChunk
        msg_chunks = [c.message if isinstance(c, ChatGenerationChunk) else c for c in chunks]
        accumulated = msg_chunks[0]
        for c in msg_chunks[1:]:
            accumulated = accumulated + c
        raw = AIMessage(content=accumulated.content, tool_calls=list(accumulated.tool_calls or []))
        fixed = self._fix(raw)
        if fixed.tool_calls and not accumulated.tool_calls:
            # Tool call encoded as text — emit a single clean chunk so LangGraph routes correctly
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_calls=fixed.tool_calls))
        else:
            for chunk in chunks:
                yield chunk


_llm = _OllamaWithToolParsing(
    model=os.environ.get("MODEL", "mistral-small:22b"),
    base_url="http://localhost:11434",
    temperature=0.1,
    num_ctx=8192,
)


class ExcelsisAgent:
    def __init__(self, store=None, vector_store=None, max_history: int = 10) -> None:
        self._graph = create_react_agent(
            model=_llm,
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        self._store        = store
        self._vector_store = vector_store
        self._history: list = []
        self._max_history   = max_history

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

    def ask(self, query: str, user: Optional[UserContext] = None) -> str:
        user     = user or ADMIN_USER
        config   = self._build_config(user)
        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=query)]
        result   = self._graph.invoke({"messages": messages}, config=config)
        final    = result["messages"][-1]
        answer   = final.content if isinstance(final, AIMessage) else str(final)
        self._append_history(query, answer)
        return answer

    async def astream_events(self, message: str, user: Optional[UserContext] = None):
        """
        Async generator yielding SSE-ready dicts.

        Event types:
          {"type": "token",     "content": "..."}
          {"type": "tool_start","tool":    "..."}
          {"type": "tool_end",  "tool":    "..."}
          {"type": "dashboard", "url":     "/dashboards/…"}
        """
        user     = user or ADMIN_USER
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
                    raw = event.get("data", {}).get("output", "")
                    # LangGraph wraps tool output in a ToolMessage in newer versions
                    output = raw.content if hasattr(raw, "content") else str(raw)
                    if output and output.startswith("/dashboards/"):
                        yield {"type": "dashboard", "url": output}

        self._append_history(message, full)

    def reset_history(self) -> None:
        self._history.clear()
