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


def _serialize_user(u: models.Utilisateur, *, with_billing: bool = True) -> dict:
    """Single source of truth for user serialization (never leaks the password
    hash). `with_billing=False` returns the minimal shape used by the admin list."""
    data = {
        "id_utilisateur": int(u.id_utilisateur),
        "nom": u.nom,
        "prenom": u.prenom,
        "email": u.email,
        "role": u.role,
    }
    if with_billing:
        data.update(
            {
                "billing_address_line1": u.billing_address_line1,
                "billing_address_line2": u.billing_address_line2,
                "billing_postal_code": u.billing_postal_code,
                "billing_city": u.billing_city,
                "billing_country": u.billing_country,
                "billing_phone": u.billing_phone,
            }
        )
    return data


@router.get("/", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    # Keep output minimal: no password hash
    return [_serialize_user(u, with_billing=False) for u in user_crud.list(db)]


@router.get("/me", response_model=UserRead)
def get_me(current_user: models.Utilisateur = Depends(get_current_user)):
    return _serialize_user(current_user)


@router.put("/me", response_model=UserRead)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user: models.Utilisateur = Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    updated = crud_user.update_user(db, int(current_user.id_utilisateur), data)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(updated)


@router.get("/me/export")
def export_me(db: Session = Depends(get_db), current_user: models.Utilisateur = Depends(get_current_user)):
    """RGPD (art. 20) / nLPD — droit a la portabilite.

    Exporte l'ensemble des donnees personnelles de l'utilisateur connecte
    (profil, commandes, scans ISBN) dans un format structure et reutilisable.
    """
    u = current_user
    commandes = (
        db.query(models.Commande)
        .filter(models.Commande.id_utilisateur == u.id_utilisateur)
        .all()
    )
    scans = (
        db.query(models.ScanISBN)
        .filter(models.ScanISBN.id_utilisateur == u.id_utilisateur)
        .all()
    )
    return {
        "utilisateur": _serialize_user(u),
        "commandes": [
            {
                "id_commande": int(c.id_commande),
                "numero_commande": c.numero_commande,
                "statut": c.statut,
                "montant_total_chf": float(c.montant_total_chf),
                "date_commande": str(c.date_commande),
            }
            for c in commandes
        ],
        "scans_isbn": [
            {
                "id_scan_isbn": int(s.id_scan_isbn),
                "isbn_lu": s.isbn_lu,
                "valide": bool(s.valide),
                "date_scan": str(s.date_scan),
            }
            for s in scans
        ],
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(db: Session = Depends(get_db), current_user: models.Utilisateur = Depends(get_current_user)):
    """RGPD (art. 17) / nLPD — droit a l'effacement (anonymisation).

    Les donnees personnelles du compte sont effacees, mais la ligne et les
    commandes sont conservees pour respecter l'obligation legale de
    conservation des justificatifs comptables (cf. politique de confidentialite).
    """
    u = current_user
    uid = int(u.id_utilisateur)
    u.nom = "Compte supprime"
    u.prenom = ""
    u.email = f"deleted-{uid}@anonymized.invalid"
    u.mot_de_passe_hash = None
    u.google_id = None
    u.billing_address_line1 = None
    u.billing_address_line2 = None
    u.billing_postal_code = None
    u.billing_city = None
    u.billing_country = None
    u.billing_phone = None
    db.add(u)
    db.commit()
    return None


@router.get("/{id_utilisateur}", response_model=UserRead)
def get_user(id_utilisateur: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    u = user_crud.get(db, id_utilisateur)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(u)


@router.delete("/{id_utilisateur}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(id_utilisateur: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if not user_crud.delete(db, id_utilisateur):
        raise HTTPException(status_code=404, detail="User not found")
    return None

@router.put("/{id_utilisateur}", response_model=UserRead)
def update_user(id_utilisateur: int, user_update: dict, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    updated = crud_user.update_user(db, id_utilisateur, user_update)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(updated)

