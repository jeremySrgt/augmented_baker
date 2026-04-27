from langchain.agents.middleware import ModelRequest, dynamic_prompt

from app.agent.context import build_stock_alert_briefing
from app.agent.prompts import SYSTEM_PROMPT
from app.repositories.notion import get_notion_repository


@dynamic_prompt
async def stock_alert_briefing_middleware(request: ModelRequest) -> str:
    section = await build_stock_alert_briefing(get_notion_repository())
    if section is None:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\n{section}"
