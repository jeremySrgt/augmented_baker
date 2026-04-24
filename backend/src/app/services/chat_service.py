from collections.abc import AsyncIterator

from langchain.chat_models import init_chat_model

from app.config import settings
from app.prompts import SYSTEM_PROMPT


class ChatService:
    def __init__(self) -> None:
        self._model = init_chat_model(
            settings.LLM_MODEL,
            model_provider=settings.LLM_PROVIDER,
            api_key=settings.ANTHROPIC_API_KEY.get_secret_value(),
        )

    async def stream(self, message: str) -> AsyncIterator[str]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        async for chunk in self._model.astream(messages):
            if chunk.text:
                yield chunk.text
