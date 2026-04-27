from typing import Annotated

from langchain.tools import tool

from app.repositories.notion import NotionUnavailable, databases as DB, get_notion_repository

_DEFAULT_LIMIT = 25


async def _query(database: DB.NotionDatabase, query: str | None, limit: int) -> list[dict] | dict:
    try:
        return await get_notion_repository().query(database, query, limit)
    except NotionUnavailable as exc:
        return {"error": exc.message}


@tool
async def stock_ingredients(
        query: Annotated[str | None, "Filtre optionnel sur le nom de l'ingrédient (ex: 'farine'')"] = None,
        limit: Annotated[int, "Nombre max de lignes (1-100, défaut 25)"] = _DEFAULT_LIMIT
) -> list[dict] | dict:
    """Lit la base "Stock Ingrédients" de Madeleine.

    Contient l'inventaire en temps réel des ingrédients de la boulangerie : farine, beurre,
    levure, sucre, oeufs, etc. Chaque ligne donne le nom de l'ingrédient, la quantité en stock,
    l'unité, le seuil d'alerte et le fournisseur habituel.

    Utilise cet outil quand Madeleine demande "combien il me reste de ...", "qu'est-ce qui
    manque", ou pour vérifier un stock avant de déclencher une commande.
    """
    return await _query(DB.STOCK_INGREDIENTS, query, limit)


@tool
async def catalogue_produits(
        query: Annotated[str | None, "Filtre optionnel sur le nom de l'ingrédient (ex: 'farine'')"] = None,
        limit: Annotated[int, "Nombre max de lignes (1-100, défaut 25)"] = _DEFAULT_LIMIT
) -> list[dict] | dict:
    """Lit la base "Catalogue Produits" de Madeleine.

    Contient le catalogue des produits vendus à la boulangerie : pains, viennoiseries,
    pâtisseries, sandwichs. Chaque ligne donne le nom du produit, le prix de vente, la marge,
    la catégorie et la recette de référence.

    Utilise cet outil pour répondre aux questions sur les prix, les marges, ce qui se vend,
    les nouveautés au catalogue.
    """
    return await _query(DB.CATALOGUE_PRODUITS, query, limit)


@tool
async def historique_ventes(
        query: Annotated[str | None, "Filtre optionnel sur le nom de l'ingrédient (ex: 'farine'')"] = None,
        limit: Annotated[int, "Nombre max de lignes (1-100, défaut 25)"] = _DEFAULT_LIMIT
) -> list[dict] | dict:
    """Lit la base "Historique Ventes" de Madeleine.

    Contient l'historique des ventes journalières de la boulangerie : date, produit, quantité
    vendue, chiffre d'affaires. Plusieurs mois d'historique permettent de voir les tendances
    par produit, par jour de la semaine, par saison.

    Utilise cet outil pour répondre aux questions sur ce qui s'est vendu, les tendances, les
    performances d'un produit, le chiffre d'affaires d'une période.
    """
    return await _query(DB.HISTORIQUE_VENTES, query, limit)


@tool
async def commandes_fournisseurs(
        query: Annotated[str | None, "Filtre optionnel sur le nom de l'ingrédient (ex: 'farine'')"] = None,
        limit: Annotated[int, "Nombre max de lignes (1-100, défaut 25)"] = _DEFAULT_LIMIT
) -> list[dict] | dict:
    """Lit la base "Commandes Fournisseurs" de Madeleine.

    Contient les commandes passées aux fournisseurs (Marcel pour la farine, le crémier, etc.) :
    date de commande, fournisseur, articles commandés, montant, statut (en attente, livrée,
    facturée), date de livraison prévue.

    Utilise cet outil pour répondre aux questions sur les commandes en cours, les retards de
    livraison, l'historique avec un fournisseur, les sommes dues.
    """
    return await _query(DB.COMMANDES_FOURNISSEURS, query, limit)


NOTION_TOOLS = [
    stock_ingredients,
    catalogue_produits,
    historique_ventes,
    commandes_fournisseurs,
]
