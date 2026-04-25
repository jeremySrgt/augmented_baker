from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


class ResumeRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    action: Literal["approve", "reject", "edit"]
    payload: dict[str, Any] | None = None


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    id: str
    name: str
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    id: str
    content: Any
    is_error: bool = False


class InterruptEvent(BaseModel):
    type: Literal["interrupt"] = "interrupt"
    id: str
    kind: str
    email: dict[str, Any] | None = None
    notion_row: dict[str, Any] | None = None
    supplier: dict[str, Any] | None = None


ChatStreamEvent = Annotated[
    TokenEvent | ToolCallEvent | ToolResultEvent | InterruptEvent,
    Field(discriminator="type"),
]
