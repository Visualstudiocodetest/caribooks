from typing import List, Optional
from domain.book import Book
from infrastructure.db import SessionLocal
from infrastructure import crud_book

class BookService:
    def __init__(self, db_session=None):
        self.db_session = db_session or SessionLocal()

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
