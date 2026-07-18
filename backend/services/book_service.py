from typing import List, Optional

from fastapi import HTTPException

from domain.book import Book
from infrastructure.db import SessionLocal
from infrastructure import crud_book, models
from services.image_service import download_image

class BookService:
    def __init__(self, db_session=None):
        self.db_session = db_session or SessionLocal()

    def create_book_from_input(self, book_in, base_url: str = "") -> Book:
        """Create a book from the API input DTO.

        Owns the business rules that used to be copy-pasted in the two router
        handlers (create_book / create_book_no_slash): downloading an external
        cover into our static folder, required-field validation, and defaulting
        the TypeObjet/EtatUsure foreign keys when the client didn't supply valid
        ones. The router is now a thin adapter.
        """
        image_link = self._resolve_image_link(book_in.image_link, base_url)
        self._validate_book_input(book_in)
        type_id = self._ensure_type_objet(getattr(book_in, "id_type_objet", None))
        etat_id = self._ensure_etat_usure(getattr(book_in, "id_etat_usure", None))

        book = Book(
            id_article=0,  # Will be set by DB
            id_type_objet=type_id,
            id_etat_usure=etat_id,
            titre=book_in.titre,
            isbn=book_in.isbn,
            auteur=book_in.auteur,
            editeur=book_in.editeur,
            date_publication=book_in.date_publication,
            langue=book_in.langue,
            description=book_in.description,
            image_link=image_link,
            prix_chf=book_in.prix_chf,
            actif=book_in.actif,
        )
        return self.create_book(book)

    @staticmethod
    def _resolve_image_link(image_link: Optional[str], base_url: str) -> Optional[str]:
        """If an external cover URL is given, download it and serve it from our
        static folder; on any failure keep the original link."""
        original = image_link
        try:
            if image_link and image_link.lower().startswith(("http://", "https://")) and "/static/images/" not in image_link:
                rel = download_image(image_link)
                base = base_url.rstrip("/") if base_url else ""
                return f"{base}{rel}" if base else rel
        except Exception:
            return original
        return image_link

    @staticmethod
    def _validate_book_input(book_in) -> None:
        if not (book_in.titre and book_in.titre.strip()):
            raise HTTPException(status_code=400, detail="Titre obligatoire")
        if not (book_in.isbn and book_in.isbn.strip()):
            raise HTTPException(status_code=400, detail="ISBN obligatoire")
        if not (book_in.auteur and book_in.auteur.strip()):
            raise HTTPException(status_code=400, detail="Auteur obligatoire")
        if book_in.prix_chf is None or book_in.prix_chf < 0:
            raise HTTPException(status_code=400, detail="Prix invalide")

    def _ensure_type_objet(self, provided_id) -> int:
        """Resolve the TypeObjet id: prefer the provided id, then a 'BOOK'/'Livre'
        row, else create a sensible default."""
        db = self.db_session
        obj = db.query(models.TypeObjet).filter(models.TypeObjet.id_type_objet == provided_id).first()
        if not obj:
            obj = db.query(models.TypeObjet).filter(models.TypeObjet.code == "BOOK").first()
        if not obj:
            obj = db.query(models.TypeObjet).filter(models.TypeObjet.libelle == "Livre").first()
        if not obj:
            obj = models.TypeObjet(libelle="Livre", code="BOOK", description="Type par défaut")
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj.id_type_objet

    def _ensure_etat_usure(self, provided_id) -> int:
        """Resolve the EtatUsure id: prefer the provided id, then a 'Bon' row, then
        any existing row, else create a sensible default."""
        db = self.db_session
        etat = db.query(models.EtatUsure).filter(models.EtatUsure.id_etat_usure == provided_id).first()
        if not etat:
            etat = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == "Bon").first()
        if not etat:
            etat = db.query(models.EtatUsure).first()
        if not etat:
            etat = models.EtatUsure(libelle="Bon", description="Etat par défaut")
            db.add(etat)
            db.commit()
            db.refresh(etat)
        return etat.id_etat_usure

    def list_books(self) -> List[Book]:
        db_livres = crud_book.get_books(self.db_session)
        return [self._to_domain_book(livre) for livre in db_livres]

    def get_book(self, id_article: int) -> Optional[Book]:
        db_livre = crud_book.get_book(self.db_session, id_article)
        if db_livre:
            return self._to_domain_book(db_livre)
        return None

    def get_book_by_isbn(self, isbn: str) -> Optional[Book]:
        db_livre = crud_book.get_book_by_isbn(self.db_session, isbn)
        if db_livre:
            return self._to_domain_book(db_livre)
        return None

    def create_book(self, book: Book) -> Book:
        db_livre = crud_book.create_book(self.db_session, book)
        return self._to_domain_book(db_livre)

    def update_book(self, id_article: int, data: dict) -> Optional[Book]:
        db_livre = crud_book.update_book(self.db_session, id_article, data)
        if db_livre:
            return self._to_domain_book(db_livre)
        return None

    def delete_book(self, id_article: int) -> bool:
        return crud_book.delete_book(self.db_session, id_article)

    def _to_domain_book(self, db_livre):
        article = db_livre.article
        etat_label = None
        try:
            etat_label = article.etat_usure.libelle if getattr(article, 'etat_usure', None) else None
        except Exception:
            etat_label = None

        categorie_labels = [c.libelle for c in article.categories] if getattr(article, 'categories', None) else []

        return Book(
            id_article=db_livre.id_article,
            titre=article.titre,
            isbn=db_livre.isbn,
            id_type_objet=article.id_type_objet,
            id_etat_usure=article.id_etat_usure,
            auteur=db_livre.auteur,
            editeur=db_livre.editeur,
            date_publication=db_livre.date_publication,
            langue=db_livre.langue,
            description=article.description,
            image_link=article.image_link,
            prix_chf=float(article.prix_chf),
            actif=article.actif,
            date_creation=article.date_creation,
            categorie_ids=[int(c.id_categorie) for c in article.categories],
            etat_libelle=etat_label,
            categorie_libelles=categorie_labels,
        )
