from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import NOTION_TOOLS
from app.config import settings


def build_agent():
    model = init_chat_model(
        settings.LLM_MODEL,
        model_provider=settings.LLM_PROVIDER,
        api_key=settings.ANTHROPIC_API_KEY.get_secret_value(),
    )
    return create_agent(model, tools=NOTION_TOOLS, system_prompt=SYSTEM_PROMPT)
