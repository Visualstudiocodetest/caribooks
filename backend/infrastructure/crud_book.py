"""
CRUD operations for the Livre table using SQLAlchemy.

- get_books: List all books
- get_book: Retrieve a book by id
- create_book: Insert a new book
- update_book: Update a book
- delete_book: Delete a book

All functions expect a SQLAlchemy Session as first argument.
"""
from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from infrastructure import models


def _ensure_default_etat_usure(db: Session, book: Any) -> int:
    """
    Ensure a Livre.id_etat_usure FK exists.
    We keep this very small and deterministic for local/dev DBs:
    try requested id, else libelle='Neuf', else first row, else create default.
    """
    etat = None
    if getattr(book, "id_etat_usure", 0):
        etat = (
            db.query(models.EtatUsure).filter(models.EtatUsure.id_etat_usure == int(book.id_etat_usure)).first()
        )
    if etat is None:
        etat = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == "Neuf").first()
    if etat is None:
        etat = db.query(models.EtatUsure).order_by(models.EtatUsure.id_etat_usure.asc()).first()
    if etat is None:
        etat = models.EtatUsure(libelle="Neuf", description="État par défaut (tests/dev)")
        db.add(etat)
        db.flush()

    return int(etat.id_etat_usure)

def _default_source_stock(db: Session) -> models.SourceStock:
    """Return the first SourceStock, creating a default one if none exists."""
    ss = db.query(models.SourceStock).order_by(models.SourceStock.id_source_stock.asc()).first()
    if ss is None:
        ss = models.SourceStock(libelle="Default", type_source="ADMIN", description="Auto-created source")
        db.add(ss)
        db.flush()
    return ss


def _add_one_to_stock(db: Session, id_livre: int, id_source_stock: Optional[int] = None) -> None:
    """Increment (or create) the stock row for `id_livre` by 1, against the
    given source (falling back to the default source when omitted/not found).

    Extracted from the four near-identical blocks that create_book used to inline
    when a book already existed or was freshly created.
    """
    ss = None
    if id_source_stock:
        ss = db.query(models.SourceStock).filter(models.SourceStock.id_source_stock == id_source_stock).first()
    if ss is None:
        ss = _default_source_stock(db)
    stock_row = (
        db.query(models.Stock)
        .filter(models.Stock.id_livre == id_livre, models.Stock.id_source_stock == ss.id_source_stock)
        .first()
    )
    if stock_row:
        stock_row.quantite_disponible = (stock_row.quantite_disponible or 0) + 1
    else:
        db.add(
            models.Stock(
                id_livre=id_livre,
                id_source_stock=ss.id_source_stock,
                quantite_disponible=1,
                quantite_reservee=0,
            )
        )


def get_books(db: Session) -> List[models.Livre]:
    """Return all books."""
    return db.query(models.Livre).all()

def get_book(db: Session, id_livre: int) -> Optional[models.Livre]:
    """Return a book by id."""
    return db.query(models.Livre).filter(models.Livre.id_livre == id_livre).first()


def get_book_by_isbn(db: Session, isbn: str) -> Optional[models.Livre]:
    """Return a book by ISBN (exact match)."""
    return db.query(models.Livre).filter(models.Livre.isbn == isbn).first()

def create_book(db: Session, book: Any) -> models.Livre:
    """Insert a new book.

    If a book with the same ISBN already exists, increment its stock by 1
    instead of creating a duplicate Livre row.
    """
    id_source_stock = getattr(book, "id_source_stock", None)

    # If identical ISBN exists, just add one to stock.
    existing = get_book_by_isbn(db, book.isbn)
    if existing:
        _add_one_to_stock(db, existing.id_livre, id_source_stock)
        # Re-list it: finalize_commande sets actif = False once a book sells
        # out, and nothing used to turn that back on when a new copy was taken
        # in. A restocked title stayed invisible in the catalogue (the home
        # page only shows books with availability > 0, and /books still marks
        # it "Inactif") even though the volunteer had just scanned it back in.
        if not existing.actif:
            existing.actif = True
        db.commit()
        db.refresh(existing)
        return existing

    id_etat_usure = _ensure_default_etat_usure(db, book)
    db_livre = models.Livre(
        id_etat_usure=id_etat_usure,
        sku=book.isbn,
        titre=book.titre,
        description=book.description,
        image_link=book.image_link,
        prix_chf=book.prix_chf,
        actif=book.actif,
        isbn=book.isbn,
        auteur=book.auteur,
        editeur=book.editeur,
        date_publication=book.date_publication,
        langue=book.langue,
    )
    db.add(db_livre)
    db.flush()  # Get id_livre
    _add_one_to_stock(db, db_livre.id_livre, id_source_stock)
    db.commit()
    db.refresh(db_livre)
    return db_livre

def update_book(db: Session, id_livre: int, data: dict) -> Optional[models.Livre]:
    """Update a book."""
    db_livre = db.query(models.Livre).filter(models.Livre.id_livre == id_livre).first()
    if not db_livre:
        return None
    for key, value in data.items():
        if hasattr(db_livre, key):
            setattr(db_livre, key, value)
    db.commit()
    db.refresh(db_livre)
    return db_livre

def count_book_order_lines(db: Session, id_livre: int) -> int:
    """How many order lines reference this book. ligne_commande.id_livre is
    ON DELETE RESTRICT, so a book that has ever been ordered cannot be deleted
    — the caller offers withdrawal from sale instead (see book_router)."""
    return (
        db.query(models.LigneCommande)
        .filter(models.LigneCommande.id_livre == id_livre)
        .count()
    )


def physical_quantity(db: Session, id_livre: int) -> int:
    """Copies of this book physically held across every source (shop):
    sum(quantite_disponible).

    This is deliberately NOT availability (disponible - reservee). A copy
    reserved in a customer's open cart is still on the shelf — treating it as
    "no longer in stock" would let an admin withdraw a book out from under a
    checkout in progress.
    """
    total = (
        db.query(func.sum(models.Stock.quantite_disponible))
        .filter(models.Stock.id_livre == id_livre)
        .scalar()
    )
    return max(0, int(total or 0))


def reserved_quantity(db: Session, id_livre: int) -> int:
    """Copies currently held by open carts across every source."""
    total = (
        db.query(func.sum(models.Stock.quantite_reservee))
        .filter(models.Stock.id_livre == id_livre)
        .scalar()
    )
    return max(0, int(total or 0))


def withdraw_book(db: Session, id_livre: int) -> Optional[models.Livre]:
    """Withdraw a book from sale without destroying its history.

    Used for a book that is out of stock in every shop but has already been
    ordered at least once: the order lines must stay (accounting/justificatifs,
    and ligne_commande.id_livre is ON DELETE RESTRICT anyway), so the book is
    delisted instead — `actif` is cleared, which is what keeps it out of the
    catalogue.

    Its now-empty stock rows are deliberately kept. They are harmless at
    quantity 0, stock_mouvement.id_stock references them ON DELETE RESTRICT,
    and refund_commande needs them to exist to credit a refunded copy back to
    the exact row it was sold from.
    """
    db_livre = db.query(models.Livre).filter(models.Livre.id_livre == id_livre).first()
    if not db_livre:
        return None
    db_livre.actif = False
    db.commit()
    db.refresh(db_livre)
    return db_livre


def delete_book(db: Session, id_livre: int) -> bool:
    """Delete a book."""
    db_livre = db.query(models.Livre).filter(models.Livre.id_livre == id_livre).first()
    if not db_livre:
        return False
    db.delete(db_livre)
    db.commit()
    return True
