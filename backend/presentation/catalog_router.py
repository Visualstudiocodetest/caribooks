from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from  infrastructure import models
from  infrastructure.crud_base import CrudBase
from  presentation.deps import get_db, require_admin
from  presentation.schemas import (
    CategorieCreate,
    CategorieRead,
    CategorieUpdate,
    EtatUsureCreate,
    EtatUsureRead,
    EtatUsureUpdate,
    TypeObjetCreate,
    TypeObjetRead,
    TypeObjetUpdate,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

type_objet_crud = CrudBase[models.TypeObjet](models.TypeObjet, "id_type_objet")
etat_usure_crud = CrudBase[models.EtatUsure](models.EtatUsure, "id_etat_usure")
categorie_crud = CrudBase[models.Categorie](models.Categorie, "id_categorie")


@router.get("/type-objets", response_model=list[TypeObjetRead])
def list_type_objets(db: Session = Depends(get_db)):
    return type_objet_crud.list(db)


@router.get("/type-objets/{id_type_objet}", response_model=TypeObjetRead)
def get_type_objet(id_type_objet: int, db: Session = Depends(get_db)):
    obj = type_objet_crud.get(db, id_type_objet)
    if obj is None:
        raise HTTPException(status_code=404, detail="TypeObjet not found")
    return obj


@router.post("/type-objets", response_model=TypeObjetRead, status_code=status.HTTP_201_CREATED)
def create_type_objet(
    payload: TypeObjetCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = models.TypeObjet(**payload.model_dump())
    return type_objet_crud.create(db, obj)


@router.put("/type-objets/{id_type_objet}", response_model=TypeObjetRead)
def update_type_objet(
    id_type_objet: int,
    payload: TypeObjetUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    updated = type_objet_crud.update(db, id_type_objet, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="TypeObjet not found")
    return updated


@router.delete("/type-objets/{id_type_objet}", status_code=status.HTTP_204_NO_CONTENT)
def delete_type_objet(
    id_type_objet: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not type_objet_crud.delete(db, id_type_objet):
        raise HTTPException(status_code=404, detail="TypeObjet not found")
    return None


@router.get("/etat-usures", response_model=list[EtatUsureRead])
def list_etat_usures(db: Session = Depends(get_db)):
    return etat_usure_crud.list(db)


@router.get("/etat-usures/{id_etat_usure}", response_model=EtatUsureRead)
def get_etat_usure(id_etat_usure: int, db: Session = Depends(get_db)):
    obj = etat_usure_crud.get(db, id_etat_usure)
    if obj is None:
        raise HTTPException(status_code=404, detail="EtatUsure not found")
    return obj


@router.post("/etat-usures", response_model=EtatUsureRead, status_code=status.HTTP_201_CREATED)
def create_etat_usure(
    payload: EtatUsureCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = models.EtatUsure(**payload.model_dump())
    return etat_usure_crud.create(db, obj)


@router.put("/etat-usures/{id_etat_usure}", response_model=EtatUsureRead)
def update_etat_usure(
    id_etat_usure: int,
    payload: EtatUsureUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    updated = etat_usure_crud.update(db, id_etat_usure, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="EtatUsure not found")
    return updated


@router.delete("/etat-usures/{id_etat_usure}", status_code=status.HTTP_204_NO_CONTENT)
def delete_etat_usure(
    id_etat_usure: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not etat_usure_crud.delete(db, id_etat_usure):
        raise HTTPException(status_code=404, detail="EtatUsure not found")
    return None


@router.get("/categories", response_model=list[CategorieRead])
def list_categories(db: Session = Depends(get_db)):
    return categorie_crud.list(db)


@router.get("/categories/{id_categorie}", response_model=CategorieRead)
def get_categorie(id_categorie: int, db: Session = Depends(get_db)):
    obj = categorie_crud.get(db, id_categorie)
    if obj is None:
        raise HTTPException(status_code=404, detail="Categorie not found")
    return obj


@router.post("/categories", response_model=CategorieRead, status_code=status.HTTP_201_CREATED)
def create_categorie(
    payload: CategorieCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = models.Categorie(**payload.model_dump())
    return categorie_crud.create(db, obj)


@router.put("/categories/{id_categorie}", response_model=CategorieRead)
def update_categorie(
    id_categorie: int,
    payload: CategorieUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    updated = categorie_crud.update(db, id_categorie, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Categorie not found")
    return updated


@router.delete("/categories/{id_categorie}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categorie(
    id_categorie: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not categorie_crud.delete(db, id_categorie):
        raise HTTPException(status_code=404, detail="Categorie not found")
    return None

