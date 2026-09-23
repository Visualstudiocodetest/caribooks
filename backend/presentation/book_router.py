from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from infrastructure import crud_book, models
from presentation.deps import AdminUser, DbSession
from presentation.schemas import BookCreate, BookRead, BookUpdate
from services.book_service import BookService
from services.rate_limit import check_rate_limit

router = APIRouter(prefix="/books", tags=["books"])

# Shared across requests (module-level, not per-call) so repeated ISBN scans
# reuse the same TCP/TLS connection to openlibrary.org instead of paying a
# fresh handshake every time. Measured impact: ~2-3s per lookup with a
# throwaway httpx.get() each call, dropping to ~0.3-0.8s once the connection
# is warm -- the dominant source of "scanning feels slow" for a volunteer
# scanning many books in a row. httpx.Client is documented as thread-safe for
# exactly this kind of shared, long-lived use (FastAPI runs sync routes like
# this one in a thread pool). follow_redirects is required: /isbn/{isbn}.json
# always 302s to the canonical /books/{OLID}.json edition page.
_openlibrary_client = httpx.Client(
    timeout=8.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    follow_redirects=True,
)

# Max number of authors to resolve names for per lookup. Author names aren't
# inlined in the edition JSON (only /authors/{key} references are), so each
# one costs an extra request; capped so a many-author anthology can't stall a
# scan.
_MAX_AUTHORS_RESOLVED = 3


def _to_book_read(db_livre: models.Livre) -> BookRead:
    etat_label = db_livre.etat_usure.libelle if getattr(db_livre, "etat_usure", None) else None
    return BookRead(
        id_livre=int(db_livre.id_livre),
        id_etat_usure=int(db_livre.id_etat_usure),
        titre=db_livre.titre,
        isbn=db_livre.isbn,
        auteur=db_livre.auteur,
        editeur=db_livre.editeur,
        date_publication=db_livre.date_publication,
        langue=db_livre.langue,
        description=db_livre.description,
        image_link=db_livre.image_link,
        prix_chf=float(db_livre.prix_chf),
        actif=bool(db_livre.actif),
        date_creation=db_livre.date_creation,
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

def _resolve_author_names(author_refs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    names = []
    for ref in author_refs[:_MAX_AUTHORS_RESOLVED]:
        key = ref.get("key")
        if not key:
            continue
        try:
            resp = _openlibrary_client.get(f"https://openlibrary.org{key}.json")
            resp.raise_for_status()
            name = resp.json().get("name")
        except (httpx.HTTPError, ValueError):
            # A single unresolvable author shouldn't fail the whole lookup --
            # the title/cover/notes are still worth returning.
            continue
        if name:
            names.append({"name": name})
    return names


def _cover_urls(cover_ids: List[int]) -> Optional[Dict[str, str]]:
    if not cover_ids:
        return None
    cover_id = cover_ids[0]
    return {
        "large": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
        "medium": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg",
        "small": f"https://covers.openlibrary.org/b/id/{cover_id}-S.jpg",
    }


@router.get("/isbn-metadata/{isbn}")
def get_isbn_metadata(isbn: str, request: Request) -> Dict[str, Any]:
    """Proxy ISBN metadata lookup via OpenLibrary (single external source).

    Uses the documented /isbn/{isbn}.json edition endpoint rather than the
    legacy /api/books?jscmd=data endpoint: OpenLibrary flags that one as
    legacy/phased-out in its own docs, and as of this writing it returns
    HTTP 404 for every request (including OpenLibrary's own documented
    example ISBN), independent of anything this backend sends.
    """
    client_host = request.client.host if request.client else "unknown"
    # Unauthenticated (scanning happens before the book exists locally), so key
    # by client IP rather than a user id. Bounds how much of the shared
    # 10-connection OpenLibrary client pool a single client can monopolize, and
    # how hard we hammer OpenLibrary's own API (see M-3).
    check_rate_limit(f"isbn_metadata:{client_host}", max_attempts=30, window_seconds=60)
    clean = isbn.strip().upper().replace("-", "")

    try:
        r = _openlibrary_client.get(f"https://openlibrary.org/isbn/{clean}.json")
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail="OpenLibrary ne répond pas (délai dépassé). Réessayez dans quelques instants.",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail="Impossible de contacter OpenLibrary (problème réseau). Vérifiez la connexion internet.",
        ) from e

    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="ISBN introuvable dans OpenLibrary")

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenLibrary a répondu avec une erreur (HTTP {r.status_code}). Le service est peut-être indisponible.",
        )

    try:
        edition = r.json()
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail="Réponse OpenLibrary illisible (format inattendu).",
        ) from e

    title = edition.get("title")
    if not title:
        raise HTTPException(status_code=404, detail="ISBN introuvable dans OpenLibrary")

    notes = edition.get("notes")
    if isinstance(notes, dict):
        notes = notes.get("value")

    return {
        "title": title,
        "subtitle": edition.get("subtitle"),
        "authors": _resolve_author_names(edition.get("authors") or []),
        "publishers": [{"name": name} for name in edition.get("publishers") or []],
        "publish_date": edition.get("publish_date"),
        "by_statement": edition.get("by_statement"),
        "cover": _cover_urls(edition.get("covers") or []),
        "notes": notes,
    }


@router.get("/{id_livre}", response_model=BookRead)
def get_book(id_livre: int, db: DbSession):
    service = BookService(db)
    book = service.get_book(id_livre)
    if not book:
        raise HTTPException(status_code=404, detail="Livre introuvable.")
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


@router.put("/{id_livre}", response_model=BookRead)
def update_book(id_livre: int, book_update: BookUpdate, request: Request, db: DbSession, _admin: AdminUser):
    service = BookService(db)
    updated = service.update_book(
        id_livre, book_update.model_dump(exclude_unset=True), base_url=str(request.base_url)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Livre introuvable.")
    return _to_book_read(updated)

@router.post("/{id_livre}/retirer", response_model=Optional[BookRead])
def remove_out_of_stock_book(id_livre: int, db: DbSession, _admin: AdminUser):
    """Retirer de la vente un livre épuisé dans tous les magasins.

    Refuse (409) tant qu'il reste au moins un exemplaire disponible. Le livre
    est supprimé s'il n'a jamais été commandé ; sinon il est désactivé
    (`actif = false`) pour préserver les lignes de commande existantes, et ses
    lignes de stock vides sont supprimées. Renvoie le livre retiré, ou `null`
    lorsqu'il a pu être supprimé définitivement.
    """
    service = BookService(db)
    withdrawn = service.remove_out_of_stock_book(id_livre)
    return _to_book_read(withdrawn) if withdrawn else None


@router.delete("/{id_livre}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(id_livre: int, db: DbSession, _admin: AdminUser):
    service = BookService(db)
    if service.get_book(id_livre) is None:
        raise HTTPException(status_code=404, detail="Livre introuvable.")
    # ligne_commande.id_livre is ON DELETE RESTRICT: deleting a book that has
    # ever been ordered used to surface as an unhandled IntegrityError (HTTP
    # 500, "Erreur lors de la suppression" in the admin UI with no explanation
    # of what to do instead). Say so, and point at the endpoint that handles it.
    if crud_book.count_book_order_lines(db, id_livre) > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ce livre figure déjà dans des commandes et ne peut pas être supprimé. "
                "Utilisez « Retirer de la vente » pour le retirer du catalogue."
            ),
        )
    service.delete_book(id_livre)
    return None
