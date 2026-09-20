from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from infrastructure import crud_user, models
from infrastructure.crud_base import CrudBase
from presentation.auth_schemas import UserRead, UserUpdate
from presentation.deps import AdminUser, CurrentUser, DbSession
from services import order_service

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
@router.get("", response_model=list[UserRead], include_in_schema=False)
def list_users(db: DbSession, _admin: AdminUser):
    # One handler serves both "/users" and "/users/" -- see book_router.list_books
    # for why: without this, a missing/extra trailing slash gets 307-redirected
    # by FastAPI straight to this backend's own absolute origin, breaking the
    # frontend's /api/proxy rewrite (the browser follows the redirect itself,
    # turning a same-origin proxied call into a cross-origin one that also
    # drops the Authorization header per the fetch spec) -- this is exactly
    # what broke the admin Utilisateurs page.
    #
    # Keep output minimal: no password hash
    return [_serialize_user(u, with_billing=False) for u in user_crud.list(db)]


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser):
    return _serialize_user(current_user)


@router.put("/me", response_model=UserRead)
def update_me(payload: UserUpdate, db: DbSession, current_user: CurrentUser):
    data = payload.model_dump(exclude_unset=True)
    updated = crud_user.update_user(db, int(current_user.id_utilisateur), data)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(updated)


@router.get("/me/export")
def export_me(db: DbSession, current_user: CurrentUser):
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
def delete_me(db: DbSession, current_user: CurrentUser):
    """RGPD (art. 17) / nLPD — droit a l'effacement (anonymisation).

    Les donnees personnelles du compte sont effacees, mais la ligne et les
    commandes sont conservees pour respecter l'obligation legale de
    conservation des justificatifs comptables (cf. politique de confidentialite).
    """
    u = current_user
    if order_service.has_orders_blocking_deletion(db, int(u.id_utilisateur)):
        raise HTTPException(
            status_code=409,
            detail=(
                "Impossible de supprimer le compte : une ou plusieurs commandes sont "
                "encore en cours (non payees, en preparation ou en livraison). "
                "Attendez qu'elles soient finalisees, annulees ou remboursees."
            ),
        )
    crud_user.anonymize_user(db, u)
    return None


@router.get("/{id_utilisateur}", response_model=UserRead)
def get_user(id_utilisateur: int, db: DbSession, _admin: AdminUser):
    u = user_crud.get(db, id_utilisateur)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(u)


@router.delete("/{id_utilisateur}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(id_utilisateur: int, db: DbSession, _admin: AdminUser):
    """Anonymizes the target user (same rule and same effect as DELETE /users/me)
    rather than hard-deleting the row: commande.id_utilisateur is ON DELETE
    RESTRICT, so a real delete would fail with an unhandled DB error as soon as
    the user has any order on record."""
    if int(_admin.id_utilisateur) == id_utilisateur:
        raise HTTPException(status_code=400, detail="Cannot delete your own account from the admin panel")
    u = user_crud.get(db, id_utilisateur)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    if order_service.has_orders_blocking_deletion(db, id_utilisateur):
        raise HTTPException(
            status_code=409,
            detail=(
                "Impossible de supprimer cet utilisateur : une ou plusieurs commandes "
                "sont encore en cours (non payees, en preparation ou en livraison)."
            ),
        )
    crud_user.anonymize_user(db, u)
    return None

@router.put("/{id_utilisateur}", response_model=UserRead)
def update_user(id_utilisateur: int, payload: UserUpdate, db: DbSession, _admin: AdminUser):
    data = payload.model_dump(exclude_unset=True)
    if int(_admin.id_utilisateur) == id_utilisateur and data.get("role") not in (None, "admin"):
        raise HTTPException(status_code=400, detail="Cannot change your own role away from admin")
    updated = crud_user.update_user(db, id_utilisateur, data)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(updated)

