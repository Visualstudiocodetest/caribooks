from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from infrastructure import models
from presentation.deps import AdminUser, DbSession
from presentation.schemas import BookCreate, BookRead, BookUpdate
from services.book_service import BookService

router = APIRouter(prefix="/books", tags=["books"])

# Shared across requests (module-level, not per-call) so repeated ISBN scans
# reuse the same TCP/TLS connection to openlibrary.org instead of paying a
# fresh handshake every time. Measured impact: ~2-3s per lookup with a
# throwaway httpx.get() each call, dropping to ~0.3-0.8s once the connection
# is warm -- the dominant source of "scanning feels slow" for a volunteer
# scanning many books in a row. httpx.Client is documented as thread-safe for
# exactly this kind of shared, long-lived use (FastAPI runs sync routes like
# this one in a thread pool).
_openlibrary_client = httpx.Client(timeout=8.0, limits=httpx.Limits(max_keepalive_connections=5, max_connections=10))


def _to_book_read(db_livre: models.Livre) -> BookRead:
    article = db_livre.article
    etat_label = article.etat_usure.libelle if getattr(article, "etat_usure", None) else None
    return BookRead(
        id_article=int(db_livre.id_article),
        id_type_objet=int(article.id_type_objet),
        id_etat_usure=int(article.id_etat_usure),
        titre=article.titre,
        isbn=db_livre.isbn,
        auteur=db_livre.auteur,
        editeur=db_livre.editeur,
        date_publication=db_livre.date_publication,
        langue=db_livre.langue,
        description=article.description,
        image_link=article.image_link,
        prix_chf=float(article.prix_chf),
        actif=bool(article.actif),
        date_creation=article.date_creation,
        etat_libelle=etat_label,
    )


@router.get("/", response_model=List[BookRead])
@router.get("", response_model=List[BookRead], include_in_schema=False)
def list_books(db: DbSession):
    # One handler serves both "/books" and "/books/" (Next.js and direct callers
    # hit both). Release stock from expired carts so delisted books reappear once
    # available.
    from services.order_service import cleanup_expired_carts
    cleanup_expired_carts(db)
    service = BookService(db)
    return [_to_book_read(b) for b in service.list_books()]


@router.get("/by-isbn/{isbn}", response_model=Optional[BookRead])
def get_book_by_isbn(isbn: str, db: DbSession):
    # Returns null (HTTP 200) when the ISBN is not in the catalogue. This is an
    # expected case during scanning, so it must not surface as a 404 error.
    service = BookService(db)
    book = service.get_book_by_isbn(isbn)
    return _to_book_read(book) if book else None

@router.get("/isbn-metadata/{isbn}")
def get_isbn_metadata(isbn: str) -> Dict[str, Any]:
    """Proxy ISBN metadata lookup via OpenLibrary (single external source)."""
    clean = isbn.strip().upper().replace("-", "")

    try:
        r = _openlibrary_client.get(
            f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean}&format=json&jscmd=data",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="OpenLibrary ne répond pas (délai dépassé). Réessayez dans quelques instants.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Impossible de contacter OpenLibrary (problème réseau). Vérifiez la connexion internet.",
        )

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenLibrary a répondu avec une erreur (HTTP {r.status_code}). Le service est peut-être indisponible.",
        )

    try:
        data = r.json()
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Réponse OpenLibrary illisible (format inattendu).",
        )

    book = data.get(f"ISBN:{clean}")
    if book and book.get("title"):
        return book

    raise HTTPException(status_code=404, detail="ISBN introuvable dans OpenLibrary")


@router.get("/{id_article}", response_model=BookRead)
def get_book(id_article: int, db: DbSession):
    service = BookService(db)
    book = service.get_book(id_article)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return _to_book_read(book)

@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_book(book_in: BookCreate, request: Request, db: DbSession, _admin: AdminUser):
    # Thin adapter: all the business logic (image download, validation, FK
    # defaulting) lives in BookService.create_book_from_input. One handler serves
    # both "/books" and "/books/".
    service = BookService(db)
    created = service.create_book_from_input(book_in, base_url=str(request.base_url))
    return _to_book_read(created)


@router.put("/{id_article}", response_model=BookRead)
def update_book(id_article: int, book_update: BookUpdate, db: DbSession, _admin: AdminUser):
    service = BookService(db)
    updated = service.update_book(id_article, book_update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return _to_book_read(updated)

@router.delete("/{id_article}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(id_article: int, db: DbSession, _admin: AdminUser):
    service = BookService(db)
    deleted = service.delete_book(id_article)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return None
