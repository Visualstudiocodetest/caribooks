from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import get_db, require_admin
from presentation.schemas import ScanISBNCreate, ScanISBNRead, ScanISBNUpdate

router = APIRouter(prefix="/scans", tags=["scans"])

scan_crud = CrudBase[models.ScanISBN](models.ScanISBN, "id_scan_isbn")


@router.get("/", response_model=list[ScanISBNRead])
@router.get("", response_model=list[ScanISBNRead], include_in_schema=False)
def list_scans(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    # One handler serves both "/scans" and "/scans/" -- see book_router.list_books
    # for why: without this, a missing/extra trailing slash gets 307-redirected
    # by FastAPI straight to this backend's own absolute origin, which the
    # frontend's /api/proxy rewrite then can't keep transparent -- the browser
    # follows that redirect itself, turning a same-origin proxied call into a
    # genuinely cross-origin one (dropping the Authorization header per the
    # fetch spec, and hitting CORS).
    return db.query(models.ScanISBN).filter(models.ScanISBN.id_utilisateur == current_user.id_utilisateur).all()


@router.get("/{id_scan_isbn}", response_model=ScanISBNRead)
def get_scan(id_scan_isbn: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    obj = (
        db.query(models.ScanISBN)
        .filter(models.ScanISBN.id_scan_isbn == id_scan_isbn, models.ScanISBN.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="ScanISBN not found")
    return obj


@router.post("/", response_model=ScanISBNRead, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=ScanISBNRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_scan(payload: ScanISBNCreate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
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
    current_user=Depends(require_admin),
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
def delete_scan(id_scan_isbn: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
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

