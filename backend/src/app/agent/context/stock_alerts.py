import logging
from typing import Literal

from app.repositories.notion import NotionRepository, NotionUnavailable, databases as DB

logger = logging.getLogger(__name__)

_Band = Literal["sous", "proche"]


def _classify(row: dict) -> _Band | None:
    qty = row.get("Quantité en stock")
    seuil = row.get("Seuil alerte")
    if qty is None or seuil is None:
        return None
    if qty < seuil:
        return "sous"
    if qty <= seuil + 1:
        return "proche"
    return None


def _fmt_number(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).replace(".", ",")


def _render_row(row: dict) -> str | None:
    name = row.get("Ingrédient")
    qty = row.get("Quantité en stock")
    seuil = row.get("Seuil alerte")
    if name is None or qty is None or seuil is None:
        logger.warning("stock alert row missing required field: %s", row.get("id"))
        return None

    unit = row.get("Unité") or ""
    price = row.get("Prix unitaire (€)")
    supplier = row.get("Fournisseur") or "fournisseur inconnu"
    email = row.get("Email fournisseur") or "email inconnu"

    unit_suffix = f" {unit}" if unit else ""
    parts = [
        name,
        f"quantité: {_fmt_number(qty)}{unit_suffix}",
        f"seuil: {_fmt_number(seuil)}{unit_suffix}",
    ]
    if price is not None:
        parts.append(f"prix: {_fmt_number(price)} €/{unit or 'unité'}")
    parts.append(f"fournisseur: {supplier} ({email})")
    return "- " + " / ".join(parts)


def _render_section(sous: list[str], proche: list[str]) -> str:
    blocks: list[str] = ["# Alerte stock"]
    if sous:
        blocks.append("## Sous le seuil d'alerte\n" + "\n".join(sous))
    if proche:
        blocks.append("## Proche du seuil\n" + "\n".join(proche))
    return "\n\n".join(blocks)


async def build_stock_alert_briefing(repository: NotionRepository) -> str | None:
    """Read Stock Ingrédients and render the alert section, or None if nothing qualifies.

    Returns None on any failure (Notion outage, schema drift, malformed row); the
    caller falls back to the static system prompt. Failures are logged at WARNING.
    """
    try:
        rows = await repository.query(DB.STOCK_INGREDIENTS, limit=100)
    except NotionUnavailable as exc:
        logger.warning("stock alert briefing unavailable: %s", exc.message)
        return None

    try:
        sous: list[str] = []
        proche: list[str] = []
        for row in rows:
            band = _classify(row)
            if band is None:
                continue
            line = _render_row(row)
            if line is None:
                continue
            (sous if band == "sous" else proche).append(line)

        if not sous and not proche:
            return None

        sous.sort()
        proche.sort()
        return _render_section(sous, proche)
    except Exception as exc:
        logger.warning("stock alert briefing render failed: %s", exc)
        return None
