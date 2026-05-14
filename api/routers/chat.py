import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.deps import get_agent, get_current_user
from api.models import ChatRequest
from src.security import UserContext

router = APIRouter()


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    agent = get_agent(request)

    async def generate():
        try:
            async for event in agent.astream_events(body.message, user=user):
                yield f"data: {json.dumps(event)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logging.getLogger(__name__).exception("Chat stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Model error: {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
