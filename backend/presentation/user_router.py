from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infrastructure import models
from infrastructure.crud_base import CrudBase
from infrastructure import crud_user
from presentation.deps import get_db, require_admin, require_user, get_current_user
from presentation.auth_schemas import UserUpdate, UserRead


router = APIRouter(prefix="/users", tags=["users"])

user_crud = CrudBase[models.Utilisateur](models.Utilisateur, "id_utilisateur")


@router.get("/", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    # Keep output minimal: no password hash
    users = user_crud.list(db)
    return [
        {
            "id_utilisateur": int(u.id_utilisateur),
            "nom": u.nom,
            "prenom": u.prenom,
            "email": u.email,
            "role": u.role,
        }
        for u in users
    ]


@router.get("/me", response_model=UserRead)
def get_me(current_user: models.Utilisateur = Depends(get_current_user)):
    u = current_user
    return {
        "id_utilisateur": int(u.id_utilisateur),
        "nom": u.nom,
        "prenom": u.prenom,
        "email": u.email,
        "role": u.role,
        "billing_address_line1": u.billing_address_line1,
        "billing_address_line2": u.billing_address_line2,
        "billing_postal_code": u.billing_postal_code,
        "billing_city": u.billing_city,
        "billing_country": u.billing_country,
        "billing_phone": u.billing_phone,
    }


@router.put("/me", response_model=UserRead)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user: models.Utilisateur = Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    updated = crud_user.update_user(db, int(current_user.id_utilisateur), data)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id_utilisateur": int(updated.id_utilisateur),
        "nom": updated.nom,
        "prenom": updated.prenom,
        "email": updated.email,
        "role": updated.role,
        "billing_address_line1": updated.billing_address_line1,
        "billing_address_line2": updated.billing_address_line2,
        "billing_postal_code": updated.billing_postal_code,
        "billing_city": updated.billing_city,
        "billing_country": updated.billing_country,
        "billing_phone": updated.billing_phone,
    }


@router.get("/{id_utilisateur}", response_model=UserRead)
def get_user(id_utilisateur: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    u = user_crud.get(db, id_utilisateur)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id_utilisateur": int(u.id_utilisateur),
        "nom": u.nom,
        "prenom": u.prenom,
        "email": u.email,
        "role": u.role,
        "billing_address_line1": u.billing_address_line1,
        "billing_address_line2": u.billing_address_line2,
        "billing_postal_code": u.billing_postal_code,
        "billing_city": u.billing_city,
        "billing_country": u.billing_country,
        "billing_phone": u.billing_phone,
    }


@router.delete("/{id_utilisateur}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(id_utilisateur: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if not user_crud.delete(db, id_utilisateur):
        raise HTTPException(status_code=404, detail="User not found")
    return None

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserRead)
def create_user(user: dict, db: Session = Depends(get_db)):
    created = crud_user.create_user(db, user)
    return {
        "id_utilisateur": int(created.id_utilisateur),
        "nom": created.nom,
        "prenom": created.prenom,
        "email": created.email,
        "role": created.role,
        "billing_address_line1": created.billing_address_line1,
        "billing_address_line2": created.billing_address_line2,
        "billing_postal_code": created.billing_postal_code,
        "billing_city": created.billing_city,
        "billing_country": created.billing_country,
        "billing_phone": created.billing_phone,
    }
@router.put("/{id_utilisateur}", response_model=UserRead)
def update_user(id_utilisateur: int, user_update: dict, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    updated = crud_user.update_user(db, id_utilisateur, user_update)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id_utilisateur": int(updated.id_utilisateur),
        "nom": updated.nom,
        "prenom": updated.prenom,
        "email": updated.email,
        "role": updated.role,
        "billing_address_line1": updated.billing_address_line1,
        "billing_address_line2": updated.billing_address_line2,
        "billing_postal_code": updated.billing_postal_code,
        "billing_city": updated.billing_city,
        "billing_country": updated.billing_country,
        "billing_phone": updated.billing_phone,
    }


@router.get("/me", response_model=UserRead)
def get_me(current_user: models.Utilisateur = Depends(get_current_user)):
    u = current_user
    return {
        "id_utilisateur": int(u.id_utilisateur),
        "nom": u.nom,
        "prenom": u.prenom,
        "email": u.email,
        "role": u.role,
        "billing_address_line1": u.billing_address_line1,
        "billing_address_line2": u.billing_address_line2,
        "billing_postal_code": u.billing_postal_code,
        "billing_city": u.billing_city,
        "billing_country": u.billing_country,
        "billing_phone": u.billing_phone,
    }


@router.put("/me", response_model=UserRead)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user: models.Utilisateur = Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    updated = crud_user.update_user(db, int(current_user.id_utilisateur), data)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id_utilisateur": int(updated.id_utilisateur),
        "nom": updated.nom,
        "prenom": updated.prenom,
        "email": updated.email,
        "role": updated.role,
        "billing_address_line1": updated.billing_address_line1,
        "billing_address_line2": updated.billing_address_line2,
        "billing_postal_code": updated.billing_postal_code,
        "billing_city": updated.billing_city,
        "billing_country": updated.billing_country,
        "billing_phone": updated.billing_phone,
    }

