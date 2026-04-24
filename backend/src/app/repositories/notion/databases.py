from dataclasses import dataclass


@dataclass(frozen=True)
class NotionDatabase:
    name: str
    database_id: str
    data_source_id: str


STOCK_INGREDIENTS = NotionDatabase(
    name="Stock Ingrédients",
    database_id="34ab6542db3a81fbac3bd5aed82d9b69",
    data_source_id="34ab6542-db3a-8138-a133-000b989d081a",
)

CATALOGUE_PRODUITS = NotionDatabase(
    name="Catalogue Produits",
    database_id="34ab6542db3a8127b4dbe9609e9ff160",
    data_source_id="34ab6542-db3a-8124-8c93-000b93bf5e02",
)

HISTORIQUE_VENTES = NotionDatabase(
    name="Historique Ventes",
    database_id="34ab6542db3a81d78043d18bddcce89d",
    data_source_id="34ab6542-db3a-8156-a564-000b248e6078",
)

COMMANDES_FOURNISSEURS = NotionDatabase(
    name="Commandes Fournisseurs",
    database_id="34ab6542db3a81e78617e2c260aa8b1e",
    data_source_id="34ab6542-db3a-8181-bb4a-000be6b53a6d",
)
