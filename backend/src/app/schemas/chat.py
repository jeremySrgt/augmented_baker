import base64
import binascii
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

_ALLOWED_IMAGE_MIMES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    images: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("images")
    @classmethod
    def _validate_images(cls, value: list[str]) -> list[str]:
        for index, url in enumerate(value):
            if not url.startswith("data:"):
                raise ValueError(f"images[{index}]: must be a data URL")
            header, _, payload = url.partition(",")
            if not payload:
                raise ValueError(f"images[{index}]: empty payload")
            meta = header[len("data:") :]
            mime, _, encoding = meta.partition(";")
            if encoding != "base64":
                raise ValueError(
                    f"images[{index}]: only base64-encoded data URLs are supported"
                )
            if mime not in _ALLOWED_IMAGE_MIMES:
                raise ValueError(
                    f"images[{index}]: unsupported mime type {mime!r}; "
                    f"allowed: {sorted(_ALLOWED_IMAGE_MIMES)}"
                )
            try:
                decoded_size = len(base64.b64decode(payload, validate=True))
            except (binascii.Error, ValueError) as exc:
                raise ValueError(
                    f"images[{index}]: invalid base64 payload"
                ) from exc
            if decoded_size > _MAX_IMAGE_BYTES:
                raise ValueError(
                    f"images[{index}]: {decoded_size} bytes exceeds 5 MB limit"
                )
        return value


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
    # Legacy supplier-order-specific fields; new kinds use `data` instead.
    email: dict[str, Any] | None = None
    notion_row: dict[str, Any] | None = None
    supplier: dict[str, Any] | None = None
    data: dict[str, Any] | None = None


ChatStreamEvent = Annotated[
    TokenEvent | ToolCallEvent | ToolResultEvent | InterruptEvent,
    Field(discriminator="type"),
]
