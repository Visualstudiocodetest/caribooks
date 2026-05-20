from typing import Optional, List
from datetime import date, datetime

class Book:
    def __init__(
        self,
        id_article: int,
        titre: str,
        isbn: str,
        id_type_objet: int = 0,
        id_etat_usure: int = 0,
        auteur: Optional[str] = None,
        editeur: Optional[str] = None,
        date_publication: Optional[date] = None,
        langue: Optional[str] = None,
        description: Optional[str] = None,
        image_link: Optional[str] = None,
        prix_chf: float = 0.0,
        actif: bool = True,
        date_creation: Optional[datetime] = None,
        categorie_ids: Optional[List[int]] = None,
        etat_libelle: Optional[str] = None,
        categorie_libelles: Optional[List[str]] = None,
    ):
        self.id_article = id_article
        self.id_type_objet = id_type_objet
        self.id_etat_usure = id_etat_usure
        self.titre = titre
        self.isbn = isbn
        self.auteur = auteur
        self.editeur = editeur
        self.date_publication = date_publication
        self.langue = langue
        self.description = description
        self.image_link = image_link
        self.prix_chf = prix_chf
        self.actif = actif
        self.date_creation = date_creation
        self.categorie_ids = categorie_ids or []
        self.etat_libelle = etat_libelle
        self.categorie_libelles = categorie_libelles or []
