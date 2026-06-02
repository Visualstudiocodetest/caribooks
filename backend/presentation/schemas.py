from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ORMBase(BaseModel):
    model_config = {"from_attributes": True}

class BookBase(BaseModel):
    # Article fields (subset)
    id_type_objet: int = 1
    id_etat_usure: int = 1
    titre: str
    isbn: str
    auteur: Optional[str] = None
    editeur: Optional[str] = None
    date_publication: Optional[date] = None
    langue: Optional[str] = None
    description: Optional[str] = None
    image_link: Optional[str] = None
    prix_chf: float = Field(..., ge=0)
    actif: bool = True

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    id_type_objet: Optional[int] = None
    id_etat_usure: Optional[int] = None
    titre: Optional[str] = None
    isbn: Optional[str] = None
    auteur: Optional[str] = None
    editeur: Optional[str] = None
    date_publication: Optional[date] = None
    langue: Optional[str] = None
    description: Optional[str] = None
    image_link: Optional[str] = None
    prix_chf: Optional[float] = None
    actif: Optional[bool] = None

class BookRead(BookBase, ORMBase):
    id_article: int
    date_creation: datetime
    categorie_ids: List[int] = Field(default_factory=list)
    etat_libelle: Optional[str] = None
    categorie_libelles: List[str] = Field(default_factory=list)


class TypeObjetBase(BaseModel):
    libelle: str
    code: str
    description: Optional[str] = None


class TypeObjetCreate(TypeObjetBase):
    pass


class TypeObjetUpdate(BaseModel):
    libelle: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class TypeObjetRead(TypeObjetBase, ORMBase):
    id_type_objet: int


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


class CategorieBase(BaseModel):
    libelle: str
    description: Optional[str] = None


class CategorieCreate(CategorieBase):
    pass


class CategorieUpdate(BaseModel):
    libelle: Optional[str] = None
    description: Optional[str] = None


class CategorieRead(CategorieBase, ORMBase):
    id_categorie: int


class ArticleBase(BaseModel):
    id_type_objet: int
    id_etat_usure: int
    sku: str
    titre: str
    description: Optional[str] = None
    image_link: Optional[str] = None
    prix_chf: float = Field(..., ge=0)
    actif: bool = True


class ArticleCreate(ArticleBase):
    categorie_ids: List[int] = Field(default_factory=list)


class ArticleUpdate(BaseModel):
    id_type_objet: Optional[int] = None
    id_etat_usure: Optional[int] = None
    sku: Optional[str] = None
    titre: Optional[str] = None
    description: Optional[str] = None
    image_link: Optional[str] = None
    prix_chf: Optional[float] = Field(default=None, ge=0)
    actif: Optional[bool] = None
    categorie_ids: Optional[List[int]] = None


class ArticleRead(ArticleBase, ORMBase):
    id_article: int
    date_creation: datetime
    categorie_ids: List[int] = Field(default_factory=list)


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
    id_article: int
    id_source_stock: int
    quantite_disponible: int = Field(default=0, ge=0)
    quantite_reservee: int = Field(default=0, ge=0)


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    quantite_disponible: Optional[int] = Field(default=None, ge=0)
    quantite_reservee: Optional[int] = Field(default=None, ge=0)


class StockRead(StockBase, ORMBase):
    id_stock: int
    date_mise_a_jour: datetime


class CommandeBase(BaseModel):
    numero_commande: str
    montant_total_chf: float = Field(..., ge=0)
    statut: str
    shipping_method: Optional[str] = "POST"
    frais_port_chf: Optional[float] = 0.0


class CommandeCreate(CommandeBase):
    pass


class CommandeUpdate(BaseModel):
    numero_commande: Optional[str] = None
    montant_total_chf: Optional[float] = Field(default=None, ge=0)
    statut: Optional[str] = None


class CommandeRead(CommandeBase, ORMBase):
    id_commande: int
    id_utilisateur: int
    date_commande: datetime


class LigneCommandeBase(BaseModel):
    id_commande: int
    id_article: int
    quantite: int = Field(..., gt=0)
    prix_unitaire_chf: float = Field(..., ge=0)


class LigneCommandeCreate(LigneCommandeBase):
    pass


class LigneCommandeUpdate(BaseModel):
    quantite: Optional[int] = Field(default=None, gt=0)
    prix_unitaire_chf: Optional[float] = Field(default=None, ge=0)


class LigneCommandeRead(LigneCommandeBase, ORMBase):
    id_ligne_commande: int


class PaiementBase(BaseModel):
    id_commande: int
    fournisseur_paiement: str = "POSTFINANCE"
    reference_externe: str
    montant_chf: float = Field(..., gt=0)  # Must be > 0, not >= 0
    devise: str = "CHF"
    statut: str
    date_paiement: Optional[datetime] = None

    @field_validator("devise")
    @classmethod
    def _devise_chf_only(cls, v: str) -> str:
        if v != "CHF":
            raise ValueError("Only CHF is supported")
        return v


class PaiementCreate(PaiementBase):
    pass


class PaiementUpdate(BaseModel):
    fournisseur_paiement: Optional[str] = None
    reference_externe: Optional[str] = None
    montant_chf: Optional[float] = Field(default=None, ge=0)
    devise: Optional[str] = None
    statut: Optional[str] = None
    date_paiement: Optional[datetime] = None

    @field_validator("devise")
    @classmethod
    def _devise_chf_only(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v != "CHF":
            raise ValueError("Only CHF is supported")
        return v


class PaiementRead(PaiementBase, ORMBase):
    id_paiement: int


class ScanISBNBase(BaseModel):
    id_article_livre: int
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
