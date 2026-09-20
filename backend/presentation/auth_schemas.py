from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# Delivery is Switzerland-only (see CLAUDE.md); the billing address doubles as
# the shipping address (order_admin_router builds client_adresse straight from
# it, there is no separate delivery-address field), so this is the one place
# that must be enforced. Accepts the spelling in any of CH's national
# languages plus English/the ISO code, case- and accent-insensitively, and
# normalizes to a single canonical value so downstream code (e.g.
# postfinance_service's ISO-2 field) always sees the same string.
_SWISS_COUNTRY_SPELLINGS = {"suisse", "schweiz", "svizzera", "svizra", "switzerland", "ch"}


def _validate_swiss_country(v: Optional[str]) -> Optional[str]:
    if v is None or not v.strip():
        return v
    if v.strip().lower() not in _SWISS_COUNTRY_SPELLINGS:
        raise ValueError("La livraison est réservée à la Suisse (billing_country doit être 'Suisse')")
    return "Suisse"


class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    mot_de_passe: str = Field(..., min_length=8)
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_phone: Optional[str] = None

    @field_validator("billing_country")
    @classmethod
    def _country_swiss_only(cls, v: Optional[str]) -> Optional[str]:
        return _validate_swiss_country(v)

class UserRead(BaseModel):
    id_utilisateur: int
    nom: str
    prenom: str
    # Plain str, not EmailStr: this is an output schema serializing values already
    # persisted in the DB, and an anonymized account's placeholder address
    # (deleted-<id>@anonymized.invalid) fails EmailStr's reserved-TLD check --
    # re-validating a format on the way out (rather than only on write) would
    # 500 the admin user list the moment any account gets deleted.
    email: str
    role: str
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_phone: Optional[str] = None


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[EmailStr] = None
    mot_de_passe: Optional[str] = Field(default=None, min_length=6)
    role: Optional[str] = None
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_phone: Optional[str] = None

    @field_validator("billing_country")
    @classmethod
    def _country_swiss_only(cls, v: Optional[str]) -> Optional[str]:
        return _validate_swiss_country(v)

class LoginRequest(BaseModel):
    username: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class GoogleAuthRequest(BaseModel):
    credential: str
