import logging
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.dependencies import get_chat_service
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.post("/chat/stream", response_class=EventSourceResponse)
async def stream_chat(
    body: ChatRequest,
    service: ChatServiceDep,
) -> AsyncIterable[ServerSentEvent]:
    try:
        async for chunk in service.stream(body.message):
            yield ServerSentEvent(data={"content": chunk}, event="token")
    except Exception:
        logger.exception("chat stream failed mid-flight")
        yield ServerSentEvent(data={"message": "stream failed"}, event="error")
        return
    yield ServerSentEvent(data={}, event="done")
