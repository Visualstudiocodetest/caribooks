"""
CRUD operations for Book/Livre and Article tables using SQLAlchemy.

- get_books: List all books
- get_book: Retrieve a book by id
- create_book: Insert a new book
- update_book: Update a book
- delete_book: Delete a book

All functions expect a SQLAlchemy Session as first argument.
"""
from sqlalchemy.orm import Session
from infrastructure import models
from domain.book import Book
from typing import List, Optional

def _ensure_default_refs(db: Session, book: Book) -> tuple[int, int]:
    """
    Ensure Article foreign keys exist.
    We keep this very small and deterministic for local/dev DBs:
    - TypeObjet: try requested id, else code='BOOK', else first row, else create default.
    - EtatUsure: try requested id, else libelle='Neuf', else first row, else create default.
    """
    type_objet = None
    if getattr(book, "id_type_objet", 0):
        type_objet = (
            db.query(models.TypeObjet).filter(models.TypeObjet.id_type_objet == int(book.id_type_objet)).first()
        )
    if type_objet is None:
        type_objet = db.query(models.TypeObjet).filter(models.TypeObjet.code == "BOOK").first()
    if type_objet is None:
        type_objet = db.query(models.TypeObjet).order_by(models.TypeObjet.id_type_objet.asc()).first()
    if type_objet is None:
        type_objet = models.TypeObjet(libelle="Livre", code="BOOK", description="Type par défaut (tests/dev)")
        db.add(type_objet)
        db.flush()

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

    return int(type_objet.id_type_objet), int(etat.id_etat_usure)

def get_books(db: Session) -> List[models.Livre]:
    """Return all books (Livre + Article)."""
    return db.query(models.Livre).all()

def get_book(db: Session, id_article: int) -> Optional[models.Livre]:
    """Return a book by article ID."""
    return db.query(models.Livre).filter(models.Livre.id_article == id_article).first()


def get_book_by_isbn(db: Session, isbn: str) -> Optional[models.Livre]:
    """Return a book by ISBN (exact match)."""
    return db.query(models.Livre).filter(models.Livre.isbn == isbn).first()

def create_book(db: Session, book: Book) -> models.Livre:
    """Insert a new book and its article.

    If a book with the same ISBN already exists, increment its stock by 1
    instead of creating duplicate Article/Livre rows.
    """
    # If identical ISBN exists in Livre, increment stock
    existing = get_book_by_isbn(db, book.isbn)
    if existing:
        # ensure a SourceStock exists (use first existing or create a default)
        ss = db.query(models.SourceStock).order_by(models.SourceStock.id_source_stock.asc()).first()
        if ss is None:
            ss = models.SourceStock(libelle="Default", type_source="ADMIN", description="Auto-created source")
            db.add(ss)
            db.flush()

        stock_row = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == existing.id_article, models.Stock.id_source_stock == ss.id_source_stock)
            .first()
        )
        if stock_row:
            stock_row.quantite_disponible = (stock_row.quantite_disponible or 0) + 1
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_stock = models.Stock(
                id_article=existing.id_article,
                id_source_stock=ss.id_source_stock,
                quantite_disponible=1,
                quantite_reservee=0,
            )
            db.add(new_stock)
            db.commit()
            db.refresh(existing)
            return existing

    id_type_objet, id_etat_usure = _ensure_default_refs(db, book)
    # Protect against a case where an Article with this SKU already exists
    # but no corresponding Livre row exists (partial previous run). In that
    # case, attach a new Livre to the existing Article and update/create stock.
    existing_article = db.query(models.Article).filter(models.Article.sku == book.isbn).first()
    if existing_article:
        # If a Livre already exists for this article, behave like existing case
        existing_livre = db.query(models.Livre).filter(models.Livre.id_article == existing_article.id_article).first()
        if existing_livre:
            # increment stock on default source or create one
            ss = db.query(models.SourceStock).order_by(models.SourceStock.id_source_stock.asc()).first()
            if ss is None:
                ss = models.SourceStock(libelle="Default", type_source="ADMIN", description="Auto-created source")
                db.add(ss)
                db.flush()

            stock_row = (
                db.query(models.Stock)
                .filter(models.Stock.id_article == existing_livre.id_article, models.Stock.id_source_stock == ss.id_source_stock)
                .first()
            )
            if stock_row:
                stock_row.quantite_disponible = (stock_row.quantite_disponible or 0) + 1
            else:
                new_stock = models.Stock(
                    id_article=existing_livre.id_article,
                    id_source_stock=ss.id_source_stock,
                    quantite_disponible=1,
                    quantite_reservee=0,
                )
                db.add(new_stock)
            db.commit()
            db.refresh(existing_livre)
            return existing_livre

        # create the missing Livre linked to the existing Article
        db_livre = models.Livre(
            id_article=existing_article.id_article,
            isbn=book.isbn,
            auteur=book.auteur,
            editeur=book.editeur,
            date_publication=book.date_publication,
            langue=book.langue,
        )
        db.add(db_livre)
        # ensure stock exists (increment first source or create)
        ss = db.query(models.SourceStock).order_by(models.SourceStock.id_source_stock.asc()).first()
        if ss is None:
            ss = models.SourceStock(libelle="Default", type_source="ADMIN", description="Auto-created source")
            db.add(ss)
            db.flush()
        stock_row = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == existing_article.id_article, models.Stock.id_source_stock == ss.id_source_stock)
            .first()
        )
        if stock_row:
            stock_row.quantite_disponible = (stock_row.quantite_disponible or 0) + 1
        else:
            new_stock = models.Stock(id_article=existing_article.id_article, id_source_stock=ss.id_source_stock, quantite_disponible=1, quantite_reservee=0)
            db.add(new_stock)
        db.commit()
        db.refresh(db_livre)
        return db_livre

    db_article = models.Article(
        id_type_objet=id_type_objet,
        id_etat_usure=id_etat_usure,
        sku=book.isbn,
        titre=book.titre,
        description=book.description,
        image_link=book.image_link,
        prix_chf=book.prix_chf,
        actif=book.actif,
    )
    db.add(db_article)
    db.flush()  # Get id_article
    db_livre = models.Livre(
        id_article=db_article.id_article,
        isbn=book.isbn,
        auteur=book.auteur,
        editeur=book.editeur,
        date_publication=book.date_publication,
        langue=book.langue,
    )
    db.add(db_livre)
    # create initial stock entry (1) with default source
    ss = db.query(models.SourceStock).order_by(models.SourceStock.id_source_stock.asc()).first()
    if ss is None:
        ss = models.SourceStock(libelle="Default", type_source="ADMIN", description="Auto-created source")
        db.add(ss)
        db.flush()
    new_stock = models.Stock(id_article=db_article.id_article, id_source_stock=ss.id_source_stock, quantite_disponible=1, quantite_reservee=0)
    db.add(new_stock)
    db.commit()
    db.refresh(db_livre)
    return db_livre

def update_book(db: Session, id_article: int, data: dict) -> Optional[models.Livre]:
    """Update a book and/or its article. Handles categorie_ids separately."""
    db_livre = db.query(models.Livre).filter(models.Livre.id_article == id_article).first()
    if not db_livre:
        return None
    db_article = db_livre.article
    categorie_ids = data.pop("categorie_ids", None)
    for key, value in data.items():
        if hasattr(db_livre, key):
            setattr(db_livre, key, value)
        elif hasattr(db_article, key):
            setattr(db_article, key, value)
    if categorie_ids is not None:
        cats = db.query(models.Categorie).filter(models.Categorie.id_categorie.in_(categorie_ids)).all()
        db_article.categories = cats
    db.commit()
    db.refresh(db_livre)
    return db_livre

def delete_book(db: Session, id_article: int) -> bool:
    """Delete a book and its article."""
    db_livre = db.query(models.Livre).filter(models.Livre.id_article == id_article).first()
    if not db_livre:
        return False
    db.delete(db_livre)
    db.commit()
    return True
