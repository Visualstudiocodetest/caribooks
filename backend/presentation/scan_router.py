from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import get_current_user, get_db
from presentation.schemas import ScanISBNCreate, ScanISBNRead, ScanISBNUpdate

router = APIRouter(prefix="/scans", tags=["scans"])

scan_crud = CrudBase[models.ScanISBN](models.ScanISBN, "id_scan_isbn")


@router.get("/", response_model=list[ScanISBNRead])
def list_scans(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.ScanISBN).filter(models.ScanISBN.id_utilisateur == current_user.id_utilisateur).all()


@router.get("/{id_scan_isbn}", response_model=ScanISBNRead)
def get_scan(id_scan_isbn: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = (
        db.query(models.ScanISBN)
        .filter(models.ScanISBN.id_scan_isbn == id_scan_isbn, models.ScanISBN.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="ScanISBN not found")
    return obj


@router.post("/", response_model=ScanISBNRead, status_code=status.HTTP_201_CREATED)
def create_scan(payload: ScanISBNCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # ensure referenced livre exists
    livre = db.query(models.Livre).filter(models.Livre.id_article == payload.id_article_livre).first()
    if livre is None:
        raise HTTPException(status_code=404, detail="Livre not found")
    obj = models.ScanISBN(id_utilisateur=current_user.id_utilisateur, **payload.model_dump())
    return scan_crud.create(db, obj)


@router.put("/{id_scan_isbn}", response_model=ScanISBNRead)
def update_scan(
    id_scan_isbn: int,
    payload: ScanISBNUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = (
        db.query(models.ScanISBN)
        .filter(models.ScanISBN.id_scan_isbn == id_scan_isbn, models.ScanISBN.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="ScanISBN not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id_scan_isbn}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(id_scan_isbn: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = (
        db.query(models.ScanISBN)
        .filter(models.ScanISBN.id_scan_isbn == id_scan_isbn, models.ScanISBN.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="ScanISBN not found")
    db.delete(obj)
    db.commit()
    return None

