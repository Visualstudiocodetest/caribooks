import binascii
import hashlib
import hmac
from typing import Optional

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.orm import Session

from infrastructure import models

# FastAPI's security docs moved off passlib (unmaintained since 2020, and it
# imports the `crypt` module that Python 3.13 removed) to pwdlib. Bcrypt is
# kept as the algorithm so existing `$2b$...` hashes in the database stay
# verifiable with no re-hash and no migration.
_password_hash = PasswordHash((BcryptHasher(),))

# Legacy prefix: a previous revision fell back to hand-rolled PBKDF2 whenever
# the passlib/bcrypt backend failed to load. Those hashes may still exist in
# older databases, so they stay verifiable here -- but are never produced any
# more: every hash written from now on is bcrypt.
_PBKDF2_PREFIX = "pbkdf2_sha256$"
_PBKDF2_ITERATIONS = 100_000


def get_password_hash(password: str) -> str:
    return _password_hash.hash(password)


def _verify_legacy_pbkdf2(plain_password: str, hashed_password: str) -> bool:
    try:
        _, salt_hex, dk_hex = hashed_password.split("$")
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(dk_hex)
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(dk, expected)
    except (ValueError, binascii.Error):
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith(_PBKDF2_PREFIX):
        return _verify_legacy_pbkdf2(plain_password, hashed_password)
    try:
        return _password_hash.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError, TypeError):
        # Stored value isn't a hash pwdlib recognises (corrupt or truncated
        # column): treat as a failed login rather than a 500.
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
        # Only ever comes from a trusted caller: the public registration
        # schema (UserCreate) has no `role` field, so a client can never
        # inject this via POST /auth/register -- only backend/scripts/
        # seed_full.py explicitly passes role="admin" for the seeded account.
        role=user_data.get("role", "user"),
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


def anonymize_user(db: Session, user: models.Utilisateur) -> models.Utilisateur:
    """RGPD (art. 17) / nLPD — droit a l'effacement.

    Scrubs personal data on the row but keeps it (and any commandes pointing
    to it) so accounting justificatifs stay intact. Shared by self-deletion
    and admin deletion so the two paths can't drift apart.
    """
    uid = int(user.id_utilisateur)
    user.nom = "Compte supprime"
    user.prenom = ""
    user.email = f"deleted-{uid}@anonymized.invalid"
    user.mot_de_passe_hash = None
    user.google_id = None
    user.billing_address_line1 = None
    user.billing_address_line2 = None
    user.billing_postal_code = None
    user.billing_city = None
    user.billing_country = None
    user.billing_phone = None
    db.add(user)
    db.commit()
    return user


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
