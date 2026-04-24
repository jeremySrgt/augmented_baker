import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from app.agent import build_agent
from app.schemas.chat import ChatStreamEvent, TokenEvent, ToolCallEvent, ToolResultEvent


class ChatService:
    def __init__(self) -> None:
        self._agent = build_agent()

    @staticmethod
    def _decode_tool_content(content: Any) -> Any:
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        return content

    async def stream(self, message: str) -> AsyncIterator[ChatStreamEvent]:
        inputs = {"messages": [{"role": "user", "content": message}]}
        async for mode, payload in self._agent.astream(
            inputs, stream_mode=["messages", "updates"]
        ):
            if mode == "messages":
                chunk, _meta = payload
                if isinstance(chunk, AIMessageChunk) and chunk.text:
                    yield TokenEvent(content=chunk.text)
            elif mode == "updates":
                for update in payload.values():
                    if not isinstance(update, dict):
                        continue
                    for msg in update.get("messages", []):
                        if isinstance(msg, AIMessage) and msg.tool_calls:
                            for tc in msg.tool_calls:
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
