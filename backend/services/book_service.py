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
        the EtatUsure foreign key when the client didn't supply a valid one is
        handled once, in crud_book._ensure_default_etat_usure. The router is
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

    def _validate_book_input(self, book_in) -> None:
        if not (book_in.titre and book_in.titre.strip()):
            raise HTTPException(status_code=400, detail="Titre obligatoire")
        if not (book_in.isbn and book_in.isbn.strip()):
            raise HTTPException(status_code=400, detail="ISBN obligatoire")
        if not (book_in.auteur and book_in.auteur.strip()):
            raise HTTPException(status_code=400, detail="Auteur obligatoire")
        if book_in.prix_chf is None or book_in.prix_chf < 0:
            raise HTTPException(status_code=400, detail="Prix invalide")
        id_source_stock = getattr(book_in, "id_source_stock", None)
        if id_source_stock is not None:
            exists = (
                self.db_session.query(models.SourceStock)
                .filter(models.SourceStock.id_source_stock == id_source_stock)
                .first()
            )
            if exists is None:
                raise HTTPException(status_code=400, detail="Source de stock invalide")

    def list_books(self) -> list[models.Livre]:
        return crud_book.get_books(self.db_session)

    def get_book(self, id_livre: int) -> Optional[models.Livre]:
        return crud_book.get_book(self.db_session, id_livre)

    def get_book_by_isbn(self, isbn: str) -> Optional[models.Livre]:
        return crud_book.get_book_by_isbn(self.db_session, isbn)

    def create_book(self, book) -> models.Livre:
        return crud_book.create_book(self.db_session, book)

    def update_book(self, id_livre: int, data: dict) -> Optional[models.Livre]:
        return crud_book.update_book(self.db_session, id_livre, data)

    def delete_book(self, id_livre: int) -> bool:
        return crud_book.delete_book(self.db_session, id_livre)

    def remove_out_of_stock_book(self, id_livre: int) -> models.Livre:
        """Retirer de la vente un livre qui n'est plus en stock dans aucun magasin.

        Business rules, in order:
        - the book must exist;
        - it must have 0 copy physically left across every source_stock (shop),
          and no copy reserved in an open cart — a reserved copy is still on the
          shelf, so withdrawing then would pull a book out of a checkout in
          progress;
        - if it has never been ordered, the row is deleted outright;
        - if it has order lines, those must be kept (accounting justificatifs,
          and ligne_commande.id_livre is ON DELETE RESTRICT), so the book is
          withdrawn from sale instead: actif = False and its empty stock rows
          are dropped.

        Returns the withdrawn Livre, or None when the row was deleted outright.
        """
        book = crud_book.get_book(self.db_session, id_livre)
        if book is None:
            raise HTTPException(status_code=404, detail="Livre introuvable.")
        in_stock = crud_book.physical_quantity(self.db_session, id_livre)
        if in_stock > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ce livre est encore en stock ({in_stock} exemplaire"
                    f"{'s' if in_stock > 1 else ''}). Retirez d’abord le stock restant."
                ),
            )
        reserved = crud_book.reserved_quantity(self.db_session, id_livre)
        if reserved > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ce livre est réservé dans {reserved} panier"
                    f"{'s' if reserved > 1 else ''} en cours. Réessayez une fois la "
                    "réservation expirée ou la commande finalisée."
                ),
            )
        if crud_book.count_book_order_lines(self.db_session, id_livre) == 0:
            crud_book.delete_book(self.db_session, id_livre)
            return None
        return crud_book.withdraw_book(self.db_session, id_livre)
