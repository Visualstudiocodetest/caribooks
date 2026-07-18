from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from  infrastructure import models
from  infrastructure.crud_base import CrudBase
from  presentation.deps import get_db, require_admin
from  presentation.schemas import (
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
def list_sources(db: Session = Depends(get_db)):
    return source_stock_crud.list(db)


@router.get("/sources/{id_source_stock}", response_model=SourceStockRead)
def get_source(id_source_stock: int, db: Session = Depends(get_db)):
    obj = source_stock_crud.get(db, id_source_stock)
    if obj is None:
        raise HTTPException(status_code=404, detail="SourceStock not found")
    return obj


@router.post("/sources", response_model=SourceStockRead, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceStockCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = models.SourceStock(**payload.model_dump())
    return source_stock_crud.create(db, obj)


@router.put("/sources/{id_source_stock}", response_model=SourceStockRead)
def update_source(
    id_source_stock: int,
    payload: SourceStockUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    updated = source_stock_crud.update(db, id_source_stock, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="SourceStock not found")
    return updated


@router.delete("/sources/{id_source_stock}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    id_source_stock: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not source_stock_crud.delete(db, id_source_stock):
        raise HTTPException(status_code=404, detail="SourceStock not found")
    return None


@router.get("/", response_model=list[StockRead])
def list_stock(db: Session = Depends(get_db)):
    # Release stock reserved by carts whose 20-min window has expired, so the
    # catalogue reflects truly available quantities on every read.
    from services.order_service import cleanup_expired_carts
    cleanup_expired_carts(db)
    return stock_crud.list(db)


@router.get("/{id_stock}", response_model=StockRead)
def get_stock(id_stock: int, db: Session = Depends(get_db)):
    obj = stock_crud.get(db, id_stock)
    if obj is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return obj


@router.post("/", response_model=StockRead, status_code=status.HTTP_201_CREATED)
def create_stock(
    payload: StockCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = models.Stock(**payload.model_dump())
    return stock_crud.create(db, obj)


@router.put("/{id_stock}", response_model=StockRead)
def update_stock(
    id_stock: int,
    payload: StockUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    updated = stock_crud.update(db, id_stock, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return updated


@router.delete("/{id_stock}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock(
    id_stock: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
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
def increment_stock(id_stock: int, payload: StockQtyChange = StockQtyChange(), db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = _get_stock_for_update(db, id_stock)
    obj.quantite_disponible = (obj.quantite_disponible or 0) + payload.qty
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{id_stock}/decrement", response_model=StockRead)
def decrement_stock(id_stock: int, payload: StockQtyChange = StockQtyChange(), db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = _get_stock_for_update(db, id_stock)
    if (obj.quantite_disponible or 0) < payload.qty:
        raise HTTPException(status_code=400, detail="Not enough stock to decrement")
    obj.quantite_disponible = (obj.quantite_disponible or 0) - payload.qty
    db.commit()
    db.refresh(obj)
    return obj

