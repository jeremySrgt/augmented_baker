import asyncio

from langchain.agents.middleware import ModelRequest, dynamic_prompt

from app.agent.context import (
    build_now_briefing,
    build_recent_orders_briefing,
    build_stock_alert_briefing,
)
from app.agent.prompts import SYSTEM_PROMPT
from app.repositories.notion import get_notion_repository


@dynamic_prompt
async def dynamic_briefing_middleware(request: ModelRequest) -> str:
    repo = get_notion_repository()
    stock_section, orders_section = await asyncio.gather(
        build_stock_alert_briefing(repo),
        build_recent_orders_briefing(repo),
    )

    sections = [SYSTEM_PROMPT, build_now_briefing()]
    if stock_section:
        sections.append(stock_section)
    if orders_section:
        sections.append(orders_section)
    return "\n\n".join(sections)
