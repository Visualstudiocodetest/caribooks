from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from infrastructure import models
from services.book_service import BookService
from presentation.schemas import BookCreate, BookRead, BookUpdate
from presentation.deps import get_db, require_admin
import httpx

router = APIRouter(prefix="/books", tags=["books"])


def _to_book_read(db_livre: models.Livre) -> BookRead:
    article = db_livre.article
    etat_label = article.etat_usure.libelle if getattr(article, "etat_usure", None) else None
    categorie_labels = [c.libelle for c in (article.categories or [])]
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
        categorie_ids=[int(c.id_categorie) for c in (article.categories or [])],
        etat_libelle=etat_label,
        categorie_libelles=categorie_labels,
    )


@router.get("/", response_model=List[BookRead])
@router.get("", response_model=List[BookRead], include_in_schema=False)
def list_books(db: Session = Depends(get_db)):
    # One handler serves both "/books" and "/books/" (Next.js and direct callers
    # hit both). Release stock from expired carts so delisted books reappear once
    # available.
    from services.order_service import cleanup_expired_carts
    cleanup_expired_carts(db)
    service = BookService(db)
    return [_to_book_read(b) for b in service.list_books()]


@router.get("/by-isbn/{isbn}", response_model=Optional[BookRead])
def get_book_by_isbn(isbn: str, db: Session = Depends(get_db)):
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
        r = httpx.get(
            f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean}&format=json&jscmd=data",
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            book = data.get(f"ISBN:{clean}")
            if book and book.get("title"):
                return book
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="ISBN introuvable")


@router.get("/{id_article}", response_model=BookRead)
def get_book(id_article: int, db: Session = Depends(get_db)):
    service = BookService(db)
    book = service.get_book(id_article)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return _to_book_read(book)

@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_book(book_in: BookCreate, request: Request, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    # Thin adapter: all the business logic (image download, validation, FK
    # defaulting) lives in BookService.create_book_from_input. One handler serves
    # both "/books" and "/books/".
    service = BookService(db)
    created = service.create_book_from_input(book_in, base_url=str(request.base_url))
    return _to_book_read(created)


@router.put("/{id_article}", response_model=BookRead)
def update_book(id_article: int, book_update: BookUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    service = BookService(db)
    updated = service.update_book(id_article, book_update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return _to_book_read(updated)

@router.delete("/{id_article}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(id_article: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    service = BookService(db)
    deleted = service.delete_book(id_article)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return None
