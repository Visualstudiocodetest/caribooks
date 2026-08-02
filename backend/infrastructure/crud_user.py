from sqlalchemy.orm import Session
from infrastructure import models
from typing import Optional
import os
import binascii
import hashlib
import hmac


def _get_pwd_context():
    try:
        from passlib.context import CryptContext
    except Exception:
        return None
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    ctx = _get_pwd_context()
    if ctx is not None:
        try:
            return ctx.hash(password)
        except Exception:
            # bcrypt backend can be broken/mismatched in some envs; fallback to pbkdf2_hmac
            pass
    # fallback to simple pbkdf2_hmac
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return "pbkdf2_sha256$" + binascii.hexlify(salt).decode() + "$" + binascii.hexlify(dk).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    ctx = _get_pwd_context()
    if ctx is not None:
        try:
            return ctx.verify(plain_password, hashed_password)
        except Exception:
            # fallback to pbkdf2 verifier below
            pass
    # fallback verify for pbkdf2_sha256
    try:
        if not hashed_password.startswith("pbkdf2_sha256$"):
            return False
        _, salt_hex, dk_hex = hashed_password.split("$")
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(dk_hex)
        dk = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt, 100000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

def get_user_by_email(db: Session, email: str) -> Optional[models.Utilisateur]:
    return db.query(models.Utilisateur).filter(models.Utilisateur.email == email).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[models.Utilisateur]:
    return db.query(models.Utilisateur).filter(models.Utilisateur.google_id == google_id).first()


def create_oauth_user(db: Session, google_id: str, email: str, prenom: str, nom: str) -> models.Utilisateur:
    db_user = models.Utilisateur(
        nom=nom,
        prenom=prenom,
        email=email,
        mot_de_passe_hash=None,
        google_id=google_id,
        role="user",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def link_google_id(db: Session, user: models.Utilisateur, google_id: str) -> models.Utilisateur:
    user.google_id = google_id
    db.commit()
    db.refresh(user)
    return user

def create_user(db: Session, user_data: dict) -> models.Utilisateur:
    db_user = models.Utilisateur(
        nom=user_data["nom"],
        prenom=user_data["prenom"],
        email=user_data["email"],
        mot_de_passe_hash=get_password_hash(user_data["mot_de_passe"]),
        role="user",
        billing_address_line1=user_data.get("billing_address_line1"),
        billing_address_line2=user_data.get("billing_address_line2"),
        billing_postal_code=user_data.get("billing_postal_code"),
        billing_city=user_data.get("billing_city"),
        billing_country=user_data.get("billing_country"),
        billing_phone=user_data.get("billing_phone"),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, id_utilisateur: int, data: dict) -> Optional[models.Utilisateur]:
    user = db.query(models.Utilisateur).filter(models.Utilisateur.id_utilisateur == id_utilisateur).first()
    if user is None:
        return None
    # fields allowed to be updated
    allowed = [
        "nom",
        "prenom",
        "email",
        "role",
        "billing_address_line1",
        "billing_address_line2",
        "billing_postal_code",
        "billing_city",
        "billing_country",
        "billing_phone",
    ]
    for k in allowed:
        if k in data:
            setattr(user, k, data[k])
    if "mot_de_passe" in data and data.get("mot_de_passe"):
        user.mot_de_passe_hash = get_password_hash(data.get("mot_de_passe"))
    db.commit()
    db.refresh(user)
    return user
