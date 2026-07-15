from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from services.book_service import BookService
from services.image_service import download_image
from domain.book import Book
from presentation.schemas import BookCreate, BookRead, BookUpdate
from presentation.deps import get_db, require_admin
from infrastructure import models
from sqlalchemy.orm import Session
import httpx

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/", response_model=List[BookRead])
def list_books(db: Session = Depends(get_db)):
    # Release stock from expired carts so delisted books reappear once available.
    from presentation.order_router import _cleanup_expired_carts
    _cleanup_expired_carts(db)
    service = BookService(db)
    return service.list_books()


@router.get("", response_model=List[BookRead], include_in_schema=False)
def list_books_no_slash(db: Session = Depends(get_db)):
    from presentation.order_router import _cleanup_expired_carts
    _cleanup_expired_carts(db)
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
def create_book(book_in: BookCreate, request: Request, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    service = BookService(db)
    image_link = book_in.image_link
    # If an external URL is provided, try to download it and serve from our static folder
    try:
        if image_link and image_link.lower().startswith(('http://', 'https://')) and '/static/images/' not in image_link:
            try:
                rel = download_image(image_link)
                base = str(request.base_url).rstrip('/') if request is not None else ''
                image_link = f"{base}{rel}" if base else rel
            except Exception:
                # if download fails, keep original link
                pass
    except Exception:
        # ignore image handling errors
        image_link = book_in.image_link

    # Server-side validation: required fields and ensure foreign keys exist (create sensible defaults if missing)
    if not (book_in.titre and book_in.titre.strip()):
        raise HTTPException(status_code=400, detail='Titre obligatoire')
    if not (book_in.isbn and book_in.isbn.strip()):
        raise HTTPException(status_code=400, detail='ISBN obligatoire')
    if not (book_in.auteur and book_in.auteur.strip()):
        raise HTTPException(status_code=400, detail='Auteur obligatoire')
    if book_in.prix_chf is None or book_in.prix_chf < 0:
        raise HTTPException(status_code=400, detail='Prix invalide')
    # ensure referenced lists exist; create sensible defaults if missing
    # TypeObjet: prefer provided id, else look for code 'BOOK' or libelle 'Livre', else create default
    type_obj = db.query(models.TypeObjet).filter(models.TypeObjet.id_type_objet == getattr(book_in, 'id_type_objet', None)).first()
    if not type_obj:
        type_obj = db.query(models.TypeObjet).filter(models.TypeObjet.code == 'BOOK').first()
    if not type_obj:
        type_obj = db.query(models.TypeObjet).filter(models.TypeObjet.libelle == 'Livre').first()
    if not type_obj:
        type_obj = models.TypeObjet(libelle='Livre', code='BOOK', description='Type par défaut')
        db.add(type_obj)
        db.commit()
        db.refresh(type_obj)
    type_id = type_obj.id_type_objet

    # EtatUsure: prefer provided id, else look for libelle 'Bon', else any existing, else create default
    etat = db.query(models.EtatUsure).filter(models.EtatUsure.id_etat_usure == getattr(book_in, 'id_etat_usure', None)).first()
    if not etat:
        etat = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == 'Bon').first()
    if not etat:
        etat = db.query(models.EtatUsure).first()
    if not etat:
        etat = models.EtatUsure(libelle='Bon', description='Etat par défaut')
        db.add(etat)
        db.commit()
        db.refresh(etat)
    etat_id = etat.id_etat_usure

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
    # require authentication to create
    return service.create_book(book)


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_book_no_slash(book_in: BookCreate, request: Request, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    service = BookService(db)
    image_link = book_in.image_link
    try:
        if image_link and image_link.lower().startswith(('http://', 'https://')) and '/static/images/' not in image_link:
            try:
                rel = download_image(image_link)
                base = str(request.base_url).rstrip('/') if request is not None else ''
                image_link = f"{base}{rel}" if base else rel
            except Exception:
                pass
    except Exception:
        image_link = book_in.image_link
    # Server-side validation: required fields and ensure foreign keys exist (create sensible defaults if missing)
    if not (book_in.titre and book_in.titre.strip()):
        raise HTTPException(status_code=400, detail='Titre obligatoire')
    if not (book_in.isbn and book_in.isbn.strip()):
        raise HTTPException(status_code=400, detail='ISBN obligatoire')
    if not (book_in.auteur and book_in.auteur.strip()):
        raise HTTPException(status_code=400, detail='Auteur obligatoire')
    if book_in.prix_chf is None or book_in.prix_chf < 0:
        raise HTTPException(status_code=400, detail='Prix invalide')

    # ensure referenced lists exist; create sensible defaults if missing (same logic as create_book)
    type_obj = db.query(models.TypeObjet).filter(models.TypeObjet.id_type_objet == getattr(book_in, 'id_type_objet', None)).first()
    if not type_obj:
        type_obj = db.query(models.TypeObjet).filter(models.TypeObjet.code == 'BOOK').first()
    if not type_obj:
        type_obj = db.query(models.TypeObjet).filter(models.TypeObjet.libelle == 'Livre').first()
    if not type_obj:
        type_obj = models.TypeObjet(libelle='Livre', code='BOOK', description='Type par défaut')
        db.add(type_obj)
        db.commit()
        db.refresh(type_obj)
    type_id = type_obj.id_type_objet

    etat = db.query(models.EtatUsure).filter(models.EtatUsure.id_etat_usure == getattr(book_in, 'id_etat_usure', None)).first()
    if not etat:
        etat = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == 'Bon').first()
    if not etat:
        etat = db.query(models.EtatUsure).first()
    if not etat:
        etat = models.EtatUsure(libelle='Bon', description='Etat par défaut')
        db.add(etat)
        db.commit()
        db.refresh(etat)
    etat_id = etat.id_etat_usure

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
    return service.create_book(book)

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
