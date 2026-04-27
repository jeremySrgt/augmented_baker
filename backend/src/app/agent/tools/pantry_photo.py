import logging
from typing import Any

from langchain.tools import tool
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.repositories.notion import NotionUnavailable, get_notion_repository
from app.repositories.notion.databases import STOCK_INGREDIENTS

logger = logging.getLogger(__name__)


class StockObservation(BaseModel):
    ingredient: str = Field(min_length=1)
    observed_quantity: float
    unit: str | None = None
    notes: str | None = None


def _normalize(name: str) -> str:
    return name.strip().lower()


def _match_observation(
    observation: StockObservation, rows: list[dict]
) -> dict | None:
    obs_name = _normalize(observation.ingredient)
    if not obs_name:
        return None
    for row in rows:
        row_name = row.get("Ingrédient")
        if isinstance(row_name, str) and _normalize(row_name) == obs_name:
            return row
    for row in rows:
        row_name = row.get("Ingrédient")
        if not isinstance(row_name, str):
            continue
        normalized = _normalize(row_name)
        if obs_name in normalized or normalized in obs_name:
            return row
    return None


def _build_diff(
    observations: list[StockObservation], rows: list[dict]
) -> tuple[list[dict], list[dict]]:
    matched: list[dict] = []
    unmatched: list[dict] = []
    for observation in observations:
        row = _match_observation(observation, rows)
        if row is None:
            unmatched.append(
                {
                    "ingredient": observation.ingredient,
                    "observed_quantity": observation.observed_quantity,
                    "unit": observation.unit,
                    "notes": observation.notes,
                }
            )
            continue
        current = row.get("Quantité en stock")
        current_qty = float(current) if current is not None else None
        delta = (
            round(observation.observed_quantity - current_qty, 4)
            if current_qty is not None
            else None
        )
        matched.append(
            {
                "page_id": row.get("id"),
                "ingredient": row.get("Ingrédient"),
                "unit": row.get("Unité") or observation.unit,
                "current_quantity": current_qty,
                "observed_quantity": observation.observed_quantity,
                "delta": delta,
            }
        )
    return matched, unmatched


def _apply_edit_overrides(
    matched: list[dict], updates: list[dict]
) -> list[dict]:
    override_map: dict[str, float] = {}
    for entry in updates:
        page_id = entry.get("page_id")
        new_quantity = entry.get("new_quantity")
        if not isinstance(page_id, str) or not isinstance(new_quantity, (int, float)):
            continue
        override_map[page_id] = float(new_quantity)
    if not override_map:
        return matched
    result: list[dict] = []
    for row in matched:
        page_id = row.get("page_id")
        if isinstance(page_id, str) and page_id in override_map:
            result.append({**row, "observed_quantity": override_map[page_id]})
        else:
            result.append(row)
    return result


@tool
async def mettre_a_jour_stock_depuis_photo(
    observations: list[StockObservation],
) -> dict[str, Any]:
    """Met à jour la colonne "Quantité en stock" de la base "Stock Ingrédients"
    à partir des ingrédients que tu viens d'identifier sur une photo de rayon
    envoyée par Madeleine.

    Workflow : Madeleine partage une photo dans son tour, tu regardes ce qui est
    visible sur l'étagère, tu estimes pour chaque ingrédient une quantité dans
    son unité (kg, L, unités — celle de la colonne `Unité` du stock), puis tu
    appelles cet outil avec la liste structurée. L'outil compare tes observations
    au stock courant, te montre le diff sous forme de carte, et **met en pause**
    pour que Madeleine valide. Tu ne décides pas seul d'écraser le stock — c'est
    elle qui valide la carte.

    Si tu n'es pas sûr de l'unité d'un ingrédient (kg vs g, L vs unités), lis
    d'abord `stock_ingredients` pour vérifier la colonne `Unité` correspondante.
    Les ingrédients que tu nommes mais qui n'existent pas dans la base seront
    juste signalés comme "Non reconnus" sur la carte — aucun écrit ne sera
    fait pour eux.

    Args:
        observations: La liste de ce que tu as vu sur la photo. Chaque entrée :
            `ingredient` (le nom français, le plus proche possible du libellé
            Notion — ex: "Beurre", "Farine T65"), `observed_quantity` (le nombre
            estimé dans l'unité du stock), `unit` optionnel (informatif, l'outil
            écrit ta quantité dans la ligne correspondante peu importe ce que tu
            mets ici), et `notes` optionnel (par ex. "presque vide" ou "sac
            entamé").
    """
    repository = get_notion_repository()

    try:
        rows = await repository.query(STOCK_INGREDIENTS, limit=100)
    except NotionUnavailable as exc:
        return {"error": exc.message}

    matched, unmatched = _build_diff(observations, rows)

    decision = interrupt(
        {
            "kind": "pantry_stock_approval",
            "data": {"matched": matched, "unmatched": unmatched},
        }
    )

    action = (decision or {}).get("action")
    payload = (decision or {}).get("payload") or {}

    if action == "reject":
        return {
            "status": "cancelled_by_user",
            "message": (
                "Madeleine a refusé la mise à jour. Aucune ligne modifiée."
            ),
        }

    if action == "edit":
        updates = payload.get("updates")
        if isinstance(updates, list):
            matched = _apply_edit_overrides(matched, updates)
    elif action != "approve":
        return {
            "status": "cancelled_unknown_action",
            "message": (
                f"Action inconnue côté UI ({action!r}). Aucune ligne modifiée."
            ),
        }

    applied: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for row in matched:
        page_id = row.get("page_id")
        if not isinstance(page_id, str):
            continue
        new_qty = row.get("observed_quantity")
        if not isinstance(new_qty, (int, float)):
            continue
        try:
            await repository.update_page(
                STOCK_INGREDIENTS,
                page_id,
                {"Quantité en stock": {"number": float(new_qty)}},
            )
            applied.append(
                {
                    "ingredient": row.get("ingredient") or "?",
                    "quantity": float(new_qty),
                    "unit": row.get("unit"),
                    "previous_quantity": row.get("current_quantity"),
                }
            )
        except NotionUnavailable as exc:
            errors.append(
                {
                    "ingredient": row.get("ingredient") or "?",
                    "message": exc.message,
                }
            )

    logger.info(
        "pantry stock update: applied=%d, unmatched=%d, errors=%d",
        len(applied),
        len(unmatched),
        len(errors),
    )

    return {
        "status": "applied",
        "updated": len(applied),
        "applied": applied,
        "unmatched": [u["ingredient"] for u in unmatched],
        "errors": errors,
    }


PANTRY_PHOTO_TOOLS = [mettre_a_jour_stock_depuis_photo]
