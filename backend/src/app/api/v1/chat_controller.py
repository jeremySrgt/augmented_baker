import logging
import uuid
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.dependencies import get_chat_service
from app.schemas.chat import ChatRequest, TokenEvent, ToolCallEvent, ToolResultEvent
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.post("/chat/stream", response_class=EventSourceResponse)
async def stream_chat(
    body: ChatRequest,
    service: ChatServiceDep,
) -> AsyncIterable[ServerSentEvent]:
    conversation_id = body.conversation_id or str(uuid.uuid4())
    try:
        async for event in service.stream(body.message, conversation_id):
            if isinstance(event, TokenEvent):
                yield ServerSentEvent(data={"content": event.content}, event="token")
            elif isinstance(event, ToolCallEvent):
                yield ServerSentEvent(
                    data={"id": event.id, "name": event.name, "args": event.args},
                    event="tool_call",
                )
            elif isinstance(event, ToolResultEvent):
                yield ServerSentEvent(
                    data={
                        "id": event.id,
                        "content": event.content,
                        "is_error": event.is_error,
                    },
                    event="tool_result",
                )
    except Exception:
        logger.exception("chat stream failed mid-flight")
        yield ServerSentEvent(data={"message": "stream failed"}, event="error")
        return
    yield ServerSentEvent(data={"conversation_id": conversation_id}, event="done")
