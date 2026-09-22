from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ORMBase(BaseModel):
    model_config = {"from_attributes": True}

class BookBase(BaseModel):
    # Lengths mirror the livre table's columns. Without them an over-long value
    # reached MySQL and came back as an unhandled DataError — HTTP 500 with the
    # raw INSERT statement and its parameters in the response body, which both
    # leaks schema details and gives the admin nothing to act on. Pydantic now
    # rejects it as a 422 naming the offending field.
    id_etat_usure: int = 1
    titre: str = Field(..., max_length=255)
    isbn: str = Field(..., max_length=20)
    auteur: Optional[str] = Field(default=None, max_length=255)
    editeur: Optional[str] = Field(default=None, max_length=255)
    date_publication: Optional[date] = None
    langue: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    image_link: Optional[str] = Field(default=None, max_length=500)
    prix_chf: float = Field(..., ge=0)
    actif: bool = True

class BookCreate(BookBase):
    # Which SourceStock the book's initial +1 unit is credited to. Optional and
    # BookCreate-only (not part of BookBase, so it never leaks into BookRead —
    # Livre has no such column, it only steers where the Stock row lands).
    # Omitted falls back to crud_book's existing default (the oldest
    # SourceStock, auto-creating one if none exist yet).
    id_source_stock: Optional[int] = None

class BookUpdate(BaseModel):
    id_etat_usure: Optional[int] = None
    titre: Optional[str] = Field(default=None, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    auteur: Optional[str] = Field(default=None, max_length=255)
    editeur: Optional[str] = Field(default=None, max_length=255)
    date_publication: Optional[date] = None
    langue: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    image_link: Optional[str] = Field(default=None, max_length=500)
    # ge=0 matches the ck_livre_prix_chf_nonneg CHECK constraint: a negative
    # price used to pass validation here and only fail at the database.
    prix_chf: Optional[float] = Field(default=None, ge=0)
    actif: Optional[bool] = None

class BookRead(BookBase, ORMBase):
    id_livre: int
    date_creation: datetime
    etat_libelle: Optional[str] = None


class EtatUsureBase(BaseModel):
    libelle: str
    description: Optional[str] = None


class EtatUsureCreate(EtatUsureBase):
    pass


class EtatUsureUpdate(BaseModel):
    libelle: Optional[str] = None
    description: Optional[str] = None


class EtatUsureRead(EtatUsureBase, ORMBase):
    id_etat_usure: int


class SourceStockBase(BaseModel):
    libelle: str
    type_source: str
    description: Optional[str] = None


class SourceStockCreate(SourceStockBase):
    pass


class SourceStockUpdate(BaseModel):
    libelle: Optional[str] = None
    type_source: Optional[str] = None
    description: Optional[str] = None


class SourceStockRead(SourceStockBase, ORMBase):
    id_source_stock: int


class StockBase(BaseModel):
    id_livre: int
    id_source_stock: int
    quantite_disponible: int = Field(default=0, ge=0)
    quantite_reservee: int = Field(default=0, ge=0)


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    quantite_disponible: Optional[int] = Field(default=None, ge=0)
    quantite_reservee: Optional[int] = Field(default=None, ge=0)


class StockQtyChange(BaseModel):
    """Body for the admin increment/decrement endpoints. Bounds the quantity
    (previously an untyped dict, so a negative/huge value was accepted verbatim)."""
    qty: int = Field(default=1, ge=1, le=100000)


class StockRead(StockBase, ORMBase):
    id_stock: int
    date_mise_a_jour: datetime


class CommandeBase(BaseModel):
    # shipping_method is client-chosen; the fee (frais_port_chf), the order number
    # (numero_commande) and the initial statut are all server-derived — never trust
    # a price/status/identifier from the client (see order_router.py).
    shipping_method: Optional[str] = "POST"


class CommandeCreate(CommandeBase):
    # numero_commande is intentionally NOT accepted here — it is generated
    # server-side (unique, non-guessable) to avoid collisions and predictable refs.
    pass


class CommandeUpdate(BaseModel):
    shipping_method: Optional[str] = None


class CommandeRead(CommandeBase, ORMBase):
    id_commande: int
    id_utilisateur: int
    numero_commande: str
    montant_total_chf: float
    statut: str
    frais_port_chf: float
    date_commande: datetime
    cart_expires_at: Optional[datetime] = None
    # Seconds until the cart reservation expires, computed with the DB clock
    # (timezone-proof). None when there is no active reservation.
    cart_seconds_left: Optional[int] = None


class LigneCommandeBase(BaseModel):
    id_commande: int
    id_livre: int
    # Upper bound as well as gt=0: reserve_stock returns early for a livre with
    # no stock rows, so an unbounded quantite went straight into the order total.
    quantite: int = Field(..., gt=0, le=1000)


class LigneCommandeCreate(LigneCommandeBase):
    pass


class LigneCommandeUpdate(BaseModel):
    quantite: Optional[int] = Field(default=None, gt=0, le=1000)


class LigneCommandeRead(LigneCommandeBase, ORMBase):
    id_ligne_commande: int
    prix_unitaire_chf: float


class LigneCommandeAdminRead(LigneCommandeRead):
    titre_livre: Optional[str] = None
    sku_livre: Optional[str] = None


class AdminCommandeStatusUpdate(BaseModel):
    """Admin-only: unlike CommandeUpdate (customer-facing), an admin may set
    statut directly — used for corrections outside the normal advance/cancel
    state machine."""
    statut: str


class CommandeAdminRead(CommandeRead):
    client_nom: Optional[str] = None
    client_prenom: Optional[str] = None
    client_email: Optional[str] = None
    client_adresse: Optional[str] = None


class PaiementBase(BaseModel):
    # montant_chf and statut are intentionally NOT client-settable — a payment's
    # amount and status may only be derived server-side (from the owning
    # Commande) or set via a verified PostFinance/Payrexx callback (webhook
    # signature check, or a server-side status fetch). Trusting these from the
    # client allowed forging a "paid" order with an arbitrary amount. See
    # order_router.py.
    id_commande: int
    fournisseur_paiement: str = "POSTFINANCE"
    reference_externe: str
    devise: str = "CHF"
    date_paiement: Optional[datetime] = None

    @field_validator("devise")
    @classmethod
    def _devise_chf_only(cls, v: str) -> str:
        if v != "CHF":
            raise ValueError("Seul le franc suisse (CHF) est accepté.")
        return v


class PaiementCreate(PaiementBase):
    pass


class PaiementUpdate(BaseModel):
    fournisseur_paiement: Optional[str] = None
    reference_externe: Optional[str] = None
    devise: Optional[str] = None
    date_paiement: Optional[datetime] = None

    @field_validator("devise")
    @classmethod
    def _devise_chf_only(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v != "CHF":
            raise ValueError("Seul le franc suisse (CHF) est accepté.")
        return v


class PaiementRead(PaiementBase, ORMBase):
    id_paiement: int
    montant_chf: float
    statut: str


class ScanISBNBase(BaseModel):
    id_livre: int
    isbn_lu: str
    valide: bool = False


class ScanISBNCreate(ScanISBNBase):
    pass


class ScanISBNUpdate(BaseModel):
    isbn_lu: Optional[str] = None
    valide: Optional[bool] = None


class ScanISBNRead(ScanISBNBase, ORMBase):
    id_scan_isbn: int
    id_utilisateur: int
    date_scan: datetime
