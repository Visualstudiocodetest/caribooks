from typing import Optional

from fastapi import HTTPException

from infrastructure import crud_book, models
from services.image_service import download_image

class BookService:
    def __init__(self, db_session):
        self.db_session = db_session

    def create_book_from_input(self, book_in, base_url: str = "") -> models.Livre:
        """Create a book from the API input DTO.

        Owns the business rules that used to be copy-pasted in the two router
        handlers (create_book / create_book_no_slash): downloading an external
        cover into our static folder and required-field validation. Defaulting
        the TypeObjet/EtatUsure foreign keys when the client didn't supply valid
        ones is handled once, in crud_book._ensure_default_refs. The router is
        now a thin adapter.
        """
        image_link = self._resolve_image_link(book_in.image_link, base_url)
        self._validate_book_input(book_in)
        resolved = book_in.model_copy(update={"image_link": image_link})
        return self.create_book(resolved)

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

    def list_books(self) -> list[models.Livre]:
        return crud_book.get_books(self.db_session)

    def get_book(self, id_article: int) -> Optional[models.Livre]:
        return crud_book.get_book(self.db_session, id_article)

    def get_book_by_isbn(self, isbn: str) -> Optional[models.Livre]:
        return crud_book.get_book_by_isbn(self.db_session, isbn)

    def create_book(self, book) -> models.Livre:
        return crud_book.create_book(self.db_session, book)

    def update_book(self, id_article: int, data: dict) -> Optional[models.Livre]:
        return crud_book.update_book(self.db_session, id_article, data)

    def delete_book(self, id_article: int) -> bool:
        return crud_book.delete_book(self.db_session, id_article)
