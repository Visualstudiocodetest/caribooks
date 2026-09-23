from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import AdminUser, DbSession
from presentation.schemas import (
    SourceStockCreate,
    SourceStockRead,
    SourceStockUpdate,
    StockCreate,
    StockQtyChange,
    StockRead,
    StockUpdate,
)

router = APIRouter(prefix="/stock", tags=["stock"])

source_stock_crud = CrudBase[models.SourceStock](models.SourceStock, "id_source_stock")
stock_crud = CrudBase[models.Stock](models.Stock, "id_stock")


@router.get("/sources", response_model=list[SourceStockRead])
def list_sources(db: DbSession, _admin: AdminUser):
    # Explicit order (oldest first): the admin "add book" form pre-selects the
    # *last* entry of this list as the most-recently-added source, which only
    # holds if the ordering is guaranteed rather than left to MySQL's
    # unspecified default row order for an unfiltered SELECT.
    return db.query(models.SourceStock).order_by(models.SourceStock.id_source_stock.asc()).all()


@router.get("/sources/{id_source_stock}", response_model=SourceStockRead)
def get_source(id_source_stock: int, db: DbSession, _admin: AdminUser):
    obj = source_stock_crud.get(db, id_source_stock)
    if obj is None:
        raise HTTPException(status_code=404, detail="Source de stock introuvable.")
    return obj


@router.post("/sources", response_model=SourceStockRead, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceStockCreate,
    db: DbSession,
    _admin: AdminUser,
):
    obj = models.SourceStock(**payload.model_dump())
    return source_stock_crud.create(db, obj)


@router.put("/sources/{id_source_stock}", response_model=SourceStockRead)
def update_source(
    id_source_stock: int,
    payload: SourceStockUpdate,
    db: DbSession,
    _admin: AdminUser,
):
    updated = source_stock_crud.update(db, id_source_stock, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Source de stock introuvable.")
    return updated


@router.delete("/sources/{id_source_stock}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    id_source_stock: int,
    db: DbSession,
    _admin: AdminUser,
):
    if not source_stock_crud.delete(db, id_source_stock):
        raise HTTPException(status_code=404, detail="Source de stock introuvable.")
    return None


@router.get("/", response_model=list[StockRead])
@router.get("", response_model=list[StockRead], include_in_schema=False)
def list_stock(db: DbSession, _admin: AdminUser):
    # One handler serves both "/stock" and "/stock/" -- see book_router.list_books
    # for why: without this, a missing/extra trailing slash gets 307-redirected
    # by FastAPI straight to this backend's own absolute origin, breaking the
    # frontend's /api/proxy rewrite (the browser follows the redirect itself,
    # turning a same-origin proxied call into a cross-origin one).
    #
    # Release stock reserved by carts whose 20-min window has expired, so the
    # catalogue reflects truly available quantities on every read.
    from services.order_service import cleanup_expired_carts
    cleanup_expired_carts(db)
    return stock_crud.list(db)


@router.get("/availability", response_model=dict[int, int])
def stock_availability(db: DbSession, livre_ids: str | None = None):
    """Available quantity per livre in a single query — max(0, sum(disponible - reservee)).

    Replaces the frontend N+1 where every cart/catalogue item fetched the whole
    /stock/ list to compute one livre's availability. Optional `livre_ids` is a
    comma-separated filter; omit it to get the whole catalogue's availability map.
    """
    from services.order_service import cleanup_expired_carts

    cleanup_expired_carts(db)
    q = db.query(
        models.Stock.id_livre,
        func.sum(models.Stock.quantite_disponible - models.Stock.quantite_reservee),
    )
    if livre_ids:
        ids = [int(x) for x in livre_ids.split(",") if x.strip().isdigit()]
        if not ids:
            return {}
        q = q.filter(models.Stock.id_livre.in_(ids))
    rows = q.group_by(models.Stock.id_livre).all()
    return {int(id_livre): max(0, int(total or 0)) for id_livre, total in rows}


@router.get("/{id_stock}", response_model=StockRead)
def get_stock(id_stock: int, db: DbSession, _admin: AdminUser):
    obj = stock_crud.get(db, id_stock)
    if obj is None:
        raise HTTPException(status_code=404, detail="Stock introuvable.")
    return obj


@router.post("/", response_model=StockRead, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=StockRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_stock(
    payload: StockCreate,
    db: DbSession,
    _admin: AdminUser,
):
    obj = models.Stock(**payload.model_dump())
    try:
        return stock_crud.create(db, obj)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ce livre a déjà une entrée de stock pour cette source.",
        ) from e


@router.put("/{id_stock}", response_model=StockRead)
def update_stock(
    id_stock: int,
    payload: StockUpdate,
    db: DbSession,
    _admin: AdminUser,
):
    updated = stock_crud.update(db, id_stock, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Stock introuvable.")
    return updated


@router.delete("/{id_stock}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock(
    id_stock: int,
    db: DbSession,
    _admin: AdminUser,
):
    if not stock_crud.delete(db, id_stock):
        raise HTTPException(status_code=404, detail="Stock introuvable.")
    return None


def _get_stock_for_update(db: Session, id_stock: int) -> models.Stock:
    """Load a stock row with a row lock so concurrent increment/decrement calls
    can't lose updates (read-modify-write was previously unguarded)."""
    obj = (
        db.query(models.Stock)
        .filter(models.Stock.id_stock == id_stock)
        .with_for_update()
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Stock introuvable.")
    return obj


@router.post("/{id_stock}/increment", response_model=StockRead)
def increment_stock(
    id_stock: int,
    db: DbSession,
    _admin: AdminUser,
    payload: StockQtyChange | None = None,
):
    obj = _get_stock_for_update(db, id_stock)
    qty = payload.qty if payload is not None else 1
    obj.quantite_disponible = (obj.quantite_disponible or 0) + qty
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{id_stock}/decrement", response_model=StockRead)
def decrement_stock(
    id_stock: int,
    db: DbSession,
    _admin: AdminUser,
    payload: StockQtyChange | None = None,
):
    obj = _get_stock_for_update(db, id_stock)
    qty = payload.qty if payload is not None else 1
    # Never undercut what's already held by open (unexpired) carts: the rest
    # of the concurrency work in this branch relies on "every reservation is
    # backed by physical stock" holding, and checking only against the raw
    # available count let an admin decrement below quantite_reservee (see M-4).
    free = (obj.quantite_disponible or 0) - (obj.quantite_reservee or 0)  # type: ignore[operator]
    if free < qty:  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="Stock insuffisant pour effectuer ce retrait.")
    obj.quantite_disponible = (obj.quantite_disponible or 0) - qty
    db.commit()
    db.refresh(obj)
    return obj

