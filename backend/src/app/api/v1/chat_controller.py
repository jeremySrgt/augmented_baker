import logging
import uuid
from collections.abc import AsyncIterable, AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.dependencies import get_chat_service
from app.schemas.chat import (
    ChatRequest,
    ChatStreamEvent,
    InterruptEvent,
    ResumeRequest,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


async def _stream_events(
    events: AsyncIterator[ChatStreamEvent],
    conversation_id: str,
) -> AsyncIterable[ServerSentEvent]:
    interrupted = False
    try:
        async for event in events:
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
            elif isinstance(event, InterruptEvent):
                interrupted = True
                yield ServerSentEvent(
                    data={
                        "id": event.id,
                        "kind": event.kind,
                        "email": event.email,
                        "notion_row": event.notion_row,
                        "supplier": event.supplier,
                    },
                    event="interrupt",
                )
    except Exception:
        logger.exception("chat stream failed mid-flight")
        yield ServerSentEvent(data={"message": "stream failed"}, event="error")
        return
    yield ServerSentEvent(
        data={"conversation_id": conversation_id, "interrupted": interrupted},
        event="done",
    )


@router.post("/chat/stream", response_class=EventSourceResponse)
async def stream_chat(
    body: ChatRequest,
    service: ChatServiceDep,
) -> AsyncIterable[ServerSentEvent]:
    conversation_id = body.conversation_id or str(uuid.uuid4())
    async for sse in _stream_events(
        service.stream(body.message, conversation_id),
        conversation_id,
    ):
        yield sse


@router.post("/chat/resume", response_class=EventSourceResponse)
async def resume_chat(
    body: ResumeRequest,
    service: ChatServiceDep,
) -> AsyncIterable[ServerSentEvent]:
    async for sse in _stream_events(
        service.resume(body.conversation_id, body.action, body.payload),
        body.conversation_id,
    ):
        yield sse
