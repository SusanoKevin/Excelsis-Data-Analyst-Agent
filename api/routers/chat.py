import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.deps import get_agent, get_current_user, get_store, get_vec
from api.models import ChatRequest
from src.security import AccessDeniedError, UserContext

router = APIRouter()


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    agent = get_agent(request)
    store = get_store(request)
    vec = get_vec(request)

    config = {
        "configurable": {
            "user_context": user,
            "store": store,
            "vector_store": vec,
        }
    }

    async def generate():
        try:
            async for event in agent._graph.astream_events(
                {"messages": [HumanMessage(content=body.message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

                elif kind == "on_tool_start":
                    name = event.get("name", "")
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': name})}\n\n"

                elif kind == "on_tool_end":
                    name = event.get("name", "")
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': name})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except AccessDeniedError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal error — check server logs'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
