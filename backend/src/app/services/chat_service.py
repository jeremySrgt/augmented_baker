import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command, Interrupt

from app.agent import build_agent
from app.schemas.chat import (
    ChatStreamEvent,
    InterruptEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
)


def _split_data_url(data_url: str) -> tuple[str, str]:
    """Split a `data:<mime>;base64,<payload>` URL into (mime, payload).

    Raises ValueError if the URL is malformed. Validation of mime/size happens
    in the controller layer; this helper trusts its input has already passed.
    """
    if not data_url.startswith("data:"):
        raise ValueError("not a data URL")
    header, _, payload = data_url.partition(",")
    if not payload:
        raise ValueError("empty data URL payload")
    meta = header[len("data:") :]
    mime, _, encoding = meta.partition(";")
    if encoding != "base64":
        raise ValueError("only base64-encoded data URLs are supported")
    return mime, payload


def _build_user_content(message: str, images: list[str]) -> str | list[dict]:
    if not images:
        return message
    parts: list[dict] = [{"type": "text", "text": message}]
    for url in images:
        mime, b64 = _split_data_url(url)
        parts.append(
            {
                "type": "image",
                "source_type": "base64",
                "data": b64,
                "mime_type": mime,
            }
        )
    return parts


class ChatService:
    def __init__(self, checkpointer: BaseCheckpointSaver) -> None:
        self._agent = build_agent(checkpointer)

    @staticmethod
    def _decode_tool_content(content: Any) -> Any:
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        return content

    async def _iterate(
        self,
        astream: AsyncIterator[tuple[str, Any]],
    ) -> AsyncIterator[ChatStreamEvent]:
        last_tool_call_id: str | None = None
        async for mode, payload in astream:
            if mode == "messages":
                chunk, _meta = payload
                if isinstance(chunk, AIMessageChunk) and chunk.text:
                    yield TokenEvent(content=chunk.text)
                continue

            if mode != "updates":
                continue

            for node_name, update in payload.items():
                if node_name == "__interrupt__":
                    # update is a tuple/list of Interrupt objects; emit one event each.
                    interrupts = update if isinstance(update, (list, tuple)) else [update]
                    for itr in interrupts:
                        if not isinstance(itr, Interrupt):
                            continue
                        value = itr.value if isinstance(itr.value, dict) else {}
                        yield InterruptEvent(
                            id=last_tool_call_id or itr.id,
                            kind=value.get("kind", "unknown"),
                            email=value.get("email"),
                            notion_row=value.get("notion_row"),
                            supplier=value.get("supplier"),
                            data=value.get("data"),
                        )
                    continue

                if not isinstance(update, dict):
                    continue
                for msg in update.get("messages", []):
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            last_tool_call_id = tc["id"]
                            yield ToolCallEvent(
                                id=tc["id"],
                                name=tc["name"],
                                args=tc.get("args") or {},
                            )
                    elif isinstance(msg, ToolMessage):
                        content = self._decode_tool_content(msg.content)
                        is_error = (
                            getattr(msg, "status", "success") == "error"
                            or (isinstance(content, dict) and "error" in content)
                        )
                        yield ToolResultEvent(
                            id=msg.tool_call_id,
                            content=content,
                            is_error=is_error,
                        )

    async def stream(
        self,
        message: str,
        conversation_id: str,
        images: list[str] | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        content = _build_user_content(message, images or [])
        inputs = {"messages": [{"role": "user", "content": content}]}
        config = {"configurable": {"thread_id": conversation_id}}
        astream = self._agent.astream(
            inputs, stream_mode=["messages", "updates"], config=config
        )
        async for event in self._iterate(astream):
            yield event

    async def resume(
        self,
        conversation_id: str,
        action: str,
        payload: dict | None,
    ) -> AsyncIterator[ChatStreamEvent]:
        decision = {"action": action, "payload": payload}
        config = {"configurable": {"thread_id": conversation_id}}
        astream = self._agent.astream(
            Command(resume=decision),
            stream_mode=["messages", "updates"],
            config=config,
        )
        async for event in self._iterate(astream):
            yield event
