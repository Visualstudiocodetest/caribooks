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
def list_sources(db: DbSession):
    return source_stock_crud.list(db)


@router.get("/sources/{id_source_stock}", response_model=SourceStockRead)
def get_source(id_source_stock: int, db: DbSession):
    obj = source_stock_crud.get(db, id_source_stock)
    if obj is None:
        raise HTTPException(status_code=404, detail="SourceStock not found")
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
        raise HTTPException(status_code=404, detail="SourceStock not found")
    return updated


@router.delete("/sources/{id_source_stock}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    id_source_stock: int,
    db: DbSession,
    _admin: AdminUser,
):
    if not source_stock_crud.delete(db, id_source_stock):
        raise HTTPException(status_code=404, detail="SourceStock not found")
    return None


@router.get("/", response_model=list[StockRead])
@router.get("", response_model=list[StockRead], include_in_schema=False)
def list_stock(db: DbSession):
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
def stock_availability(db: DbSession, article_ids: str | None = None):
    """Available quantity per article in a single query — max(0, sum(disponible - reservee)).

    Replaces the frontend N+1 where every cart/catalogue item fetched the whole
    /stock/ list to compute one article's availability. Optional `article_ids` is a
    comma-separated filter; omit it to get the whole catalogue's availability map.
    """
    from services.order_service import cleanup_expired_carts

    cleanup_expired_carts(db)
    q = db.query(
        models.Stock.id_article,
        func.sum(models.Stock.quantite_disponible - models.Stock.quantite_reservee),
    )
    if article_ids:
        ids = [int(x) for x in article_ids.split(",") if x.strip().isdigit()]
        if not ids:
            return {}
        q = q.filter(models.Stock.id_article.in_(ids))
    rows = q.group_by(models.Stock.id_article).all()
    return {int(id_article): max(0, int(total or 0)) for id_article, total in rows}


@router.get("/{id_stock}", response_model=StockRead)
def get_stock(id_stock: int, db: DbSession):
    obj = stock_crud.get(db, id_stock)
    if obj is None:
        raise HTTPException(status_code=404, detail="Stock not found")
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
        raise HTTPException(status_code=404, detail="Stock not found")
    return updated


@router.delete("/{id_stock}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock(
    id_stock: int,
    db: DbSession,
    _admin: AdminUser,
):
    if not stock_crud.delete(db, id_stock):
        raise HTTPException(status_code=404, detail="Stock not found")
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
        raise HTTPException(status_code=404, detail="Stock not found")
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
    if (obj.quantite_disponible or 0) < qty:
        raise HTTPException(status_code=400, detail="Not enough stock to decrement")
    obj.quantite_disponible = (obj.quantite_disponible or 0) - qty
    db.commit()
    db.refresh(obj)
    return obj

