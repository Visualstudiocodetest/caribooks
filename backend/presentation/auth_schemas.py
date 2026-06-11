from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    mot_de_passe: str = Field(..., min_length=6)
    role: Optional[str] = "user"
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_phone: Optional[str] = None

class UserRead(BaseModel):
    id_utilisateur: int
    nom: str
    prenom: str
    email: EmailStr
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

class LoginRequest(BaseModel):
    username: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    credential: str
