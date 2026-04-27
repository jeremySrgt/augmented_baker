from app.agent.tools.notion import NOTION_TOOLS
from app.agent.tools.pantry_photo import PANTRY_PHOTO_TOOLS
from app.agent.tools.supplier_orders import SUPPLIER_ORDER_TOOLS

AGENT_TOOLS = [*NOTION_TOOLS, *SUPPLIER_ORDER_TOOLS, *PANTRY_PHOTO_TOOLS]

__all__ = [
    "AGENT_TOOLS",
    "NOTION_TOOLS",
    "PANTRY_PHOTO_TOOLS",
    "SUPPLIER_ORDER_TOOLS",
]
