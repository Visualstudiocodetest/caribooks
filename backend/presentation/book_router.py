from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from services.book_service import BookService
from presentation.schemas import BookCreate, BookRead, BookUpdate
from presentation.deps import get_db, require_admin
import httpx

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/", response_model=List[BookRead])
@router.get("", response_model=List[BookRead], include_in_schema=False)
def list_books(db: Session = Depends(get_db)):
    # One handler serves both "/books" and "/books/" (Next.js and direct callers
    # hit both). Release stock from expired carts so delisted books reappear once
    # available.
    from services.order_service import cleanup_expired_carts
    cleanup_expired_carts(db)
    service = BookService(db)
    return service.list_books()


@router.get("/by-isbn/{isbn}", response_model=Optional[BookRead])
def get_book_by_isbn(isbn: str, db: Session = Depends(get_db)):
    # Returns null (HTTP 200) when the ISBN is not in the catalogue. This is an
    # expected case during scanning, so it must not surface as a 404 error.
    service = BookService(db)
    return service.get_book_by_isbn(isbn)

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
    return book

@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_book(book_in: BookCreate, request: Request, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    # Thin adapter: all the business logic (image download, validation, FK
    # defaulting) lives in BookService.create_book_from_input. One handler serves
    # both "/books" and "/books/".
    service = BookService(db)
    return service.create_book_from_input(book_in, base_url=str(request.base_url))


@router.put("/{id_article}", response_model=BookRead)
def update_book(id_article: int, book_update: BookUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    service = BookService(db)
    updated = service.update_book(id_article, book_update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated

@router.delete("/{id_article}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(id_article: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    service = BookService(db)
    deleted = service.delete_book(id_article)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return None
