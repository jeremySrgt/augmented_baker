import logging

from app.repositories.notion import NotionRepository, NotionUnavailable, databases as DB

logger = logging.getLogger(__name__)

_LIMIT = 3


def _date_key(row: dict) -> str:
    # ISO date strings sort lexicographically; missing → empty → sorted last when reversed.
    return (row.get("Date commande") or {}).get("start") or ""


def _items_one_line(text: str) -> str:
    pieces = [line.lstrip("- ").strip() for line in text.splitlines() if line.strip()]
    return " ; ".join(pieces)


def _render_row(row: dict) -> str | None:
    ref = row.get("Référence commande")
    if not ref:
        logger.warning("recent order row missing reference: %s", row.get("id"))
        return None

    supplier = row.get("Fournisseur") or "fournisseur inconnu"
    status = row.get("Statut") or "statut inconnu"
    sent = (row.get("Date commande") or {}).get("start")
    items = row.get("Produits commandés") or ""

    parts = [str(ref), f"statut: {status}", f"fournisseur: {supplier}"]
    if sent:
        parts.append(f"envoyée le {sent}")
    one_line = _items_one_line(items)
    if one_line:
        parts.append(f"articles: {one_line}")
    return "- " + " / ".join(parts)


async def build_recent_orders_briefing(repository: NotionRepository) -> str | None:
    """Render the last few supplier orders (all statuses), most recent first.

    Returns None on Notion outage or if there are no orders to show.
    """
    try:
        rows = await repository.query(DB.COMMANDES_FOURNISSEURS, limit=50)
    except NotionUnavailable as exc:
        logger.warning("recent orders briefing unavailable: %s", exc.message)
        return None

    try:
        rows.sort(key=_date_key, reverse=True)
        rendered = [line for row in rows[:_LIMIT] if (line := _render_row(row)) is not None]
        if not rendered:
            return None
        return "# Dernières commandes\n" + "\n".join(rendered)
    except Exception as exc:
        logger.warning("recent orders briefing render failed: %s", exc)
        return None
