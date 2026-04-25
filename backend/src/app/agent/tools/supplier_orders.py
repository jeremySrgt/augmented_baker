import logging
from datetime import date
from typing import Any, Literal

from langchain.tools import tool
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.repositories.notion import NotionUnavailable, get_notion_repository
from app.repositories.notion.databases import COMMANDES_FOURNISSEURS

logger = logging.getLogger(__name__)


class OrderItem(BaseModel):
    ingredient: str = Field(min_length=1)
    quantity: float
    unit: str | None = None


def _format_item(item: OrderItem) -> str:
    unit = f" {item.unit}" if item.unit else ""
    return f"- {item.quantity}{unit} {item.ingredient}".rstrip()


def _draft_email(
    supplier_name: str,
    supplier_email: str,
    items: list[OrderItem],
    notes: str | None,
) -> dict[str, str]:
    items_block = "\n".join(_format_item(it) for it in items)
    notes_block = f"\n\n{notes}" if notes else ""
    body = (
        f"Bonjour {supplier_name},\n\n"
        f"Pourriez-vous me préparer la commande suivante :\n\n"
        f"{items_block}{notes_block}\n\n"
        f"Merci d'avance, je vous tiens au courant pour la livraison.\n\n"
        f"Bien cordialement,\n"
        f"Madeleine Croûton — Boulangerie Chez Madeleine"
    )
    return {
        "to": supplier_email,
        "subject": f"Commande - {supplier_name}",
        "body": body,
    }


def _build_row(
    supplier_name: str,
    supplier_email: str,
    items: list[OrderItem],
    notes: str | None,
) -> dict[str, Any]:
    today = date.today().isoformat()
    items_text = "\n".join(_format_item(it) for it in items)
    return {
        "Référence commande": {
            "title": [{"text": {"content": f"Commande {supplier_name} - {today}"}}],
        },
        "Date commande": {"date": {"start": today}},
        "Fournisseur": {"select": {"name": supplier_name}},
        "Email envoyé à": {"email": supplier_email},
        "Produits commandés": {"rich_text": [{"text": {"content": items_text}}]},
        "Statut": {"select": {"name": "Envoyée"}},
        "Notes": {"rich_text": [{"text": {"content": notes or ""}}]},
    }


def _apply_overrides(base: dict, overrides: dict | None) -> dict:
    if not overrides:
        return base
    return {**base, **overrides}


def _row_with_overrides(
    supplier_name: str,
    supplier_email: str,
    items: list[OrderItem],
    notes: str | None,
    row_overrides: dict | None,
) -> dict[str, Any]:
    row = _build_row(supplier_name, supplier_email, items, notes)
    if not row_overrides:
        return row
    # Overrides come in flat form, e.g. {"Notes": "texte édité"} — re-shape to
    # the property objects Notion expects, only for the keys we recognize.
    for key, value in row_overrides.items():
        if key == "Notes":
            row["Notes"] = {"rich_text": [{"text": {"content": value or ""}}]}
        elif key == "Produits commandés":
            row["Produits commandés"] = {"rich_text": [{"text": {"content": value or ""}}]}
        elif key == "Référence commande":
            row["Référence commande"] = {"title": [{"text": {"content": value}}]}
    return row


@tool
async def envoyer_commande_fournisseur(
    supplier_name: str,
    supplier_email: str,
    items: list[OrderItem],
    notes: str | None = None,
) -> dict[str, Any]:
    """Prépare et envoie une commande à un fournisseur, après l'aval explicite de Madeleine.

    Workflow : tu rédiges le mail, tu construis la ligne pour la base "Commandes Fournisseurs",
    puis tu **mets en pause** pour montrer le brouillon à Madeleine. Elle peut valider, refuser,
    ou éditer (corriger une ligne, modifier une note). Sur validation, tu envoies le mail
    (faussement, pour l'instant — on log juste l'action) et tu écris la ligne dans Notion.

    Avant d'appeler cet outil, tu DOIS avoir récupéré l'email du fournisseur via `stock_ingredients`
    (l'email vit dans la propriété "Email fournisseur" sur chaque ligne d'ingrédient). Si tu n'as
    pas l'email, demande-le à Madeleine ou regarde le stock.

    Args:
        supplier_name: Le nom du fournisseur, choisi parmi la liste fixe (Minoterie Dupont,
            Laiterie du Midi, Sucrerie Méridionale, Œufs Fermiers Garcin, Levures Martin,
            Sel de Camargue).
        supplier_email: L'adresse mail du fournisseur (à récupérer via `stock_ingredients`).
        items: La liste des articles à commander, chacun avec ingredient, quantity, et unit
            optionnel (kg, L, unités, g).
        notes: Précision libre à inclure dans le mail et dans la ligne Notion (urgence,
            créneau de livraison souhaité, etc.).
    """
    repository = get_notion_repository()

    email_draft = _draft_email(supplier_name, supplier_email, items, notes)
    row_draft = _build_row(supplier_name, supplier_email, items, notes)

    # interrupt() pauses the agent here; the value below is the resume payload.
    decision = interrupt(
        {
            "kind": "supplier_order_approval",
            "email": email_draft,
            "notion_row": row_draft,
            "supplier": {"name": supplier_name, "email": supplier_email},
        }
    )

    action = (decision or {}).get("action")
    overrides = (decision or {}).get("payload") or {}

    if action == "reject":
        return {
            "status": "cancelled_by_user",
            "message": (
                "Madeleine a refusé le brouillon avant l'envoi. "
                "Aucun mail n'est parti et aucune ligne n'a été créée dans Notion."
            ),
        }

    if action == "edit":
        email_draft = _apply_overrides(email_draft, overrides.get("email"))
        row_draft = _row_with_overrides(
            supplier_name,
            supplier_email,
            items,
            notes,
            overrides.get("notion_row"),
        )
    elif action != "approve":
        # Unknown action — treat as a no-op cancellation rather than blowing up the turn.
        return {
            "status": "cancelled_unknown_action",
            "message": f"Action inconnue côté UI ({action!r}). Aucune commande envoyée.",
        }

    try:
        page = await repository.create_page(COMMANDES_FOURNISSEURS, row_draft)
    except NotionUnavailable as exc:
        return {"error": exc.message}

    logger.info(
        "supplier order email -> %s: subject=%s; body_chars=%d",
        email_draft["to"],
        email_draft["subject"],
        len(email_draft["body"]),
    )

    return {"status": "sent", "order_id": page.get("id")}


SUPPLIER_ORDER_TOOLS = [envoyer_commande_fournisseur]
