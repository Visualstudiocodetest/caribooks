from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from presentation.auth_schemas import LoginRequest, UserCreate, UserRead, Token, GoogleAuthRequest
from infrastructure import crud_user
import os
import httpx
from presentation.deps import get_db, ENVIRONMENT, SECRET_KEY
from services.jwt_service import create_access_token
from services.rate_limit import check_rate_limit, reset_rate_limit

ACCESS_TOKEN_EXPIRE_MINUTES = 480

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    client_host = request.client.host if request.client else "unknown"
    # 5 registrations / 10 minutes per client — bounds automated account creation
    # and email-enumeration probing (the 400 below reveals whether an email exists).
    check_rate_limit(f"register:{client_host}", max_attempts=5, window_seconds=600)
    existing = crud_user.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud_user.create_user(db, user_in.model_dump())
    return UserRead(
        id_utilisateur= db_user.id_utilisateur,
        nom=db_user.nom,
        prenom=db_user.prenom,
        email=db_user.email,
        role=db_user.role,
        billing_address_line1=db_user.billing_address_line1,
        billing_address_line2=db_user.billing_address_line2,
        billing_postal_code=db_user.billing_postal_code,
        billing_city=db_user.billing_city,
        billing_country=db_user.billing_country,
        billing_phone=db_user.billing_phone,
    )


@router.post("/token", response_model=Token)
def login_for_access_token(payload: LoginRequest, db: Session = Depends(get_db)):
    rate_limit_key = f"token:{str(payload.username).strip().lower()}"
    # 10 attempts / 5 minutes per account — blocks password-guessing/credential
    # stuffing against a known email without depending on client IP (which is
    # unreliable behind the reverse proxy without trusted X-Forwarded-For setup).
    check_rate_limit(rate_limit_key, max_attempts=10, window_seconds=300)

    user = crud_user.get_user_by_email(db, str(payload.username))
    verified = False
    if user and user.mot_de_passe_hash:
        try:
            verified = crud_user.verify_password(str(payload.password), str(user.mot_de_passe_hash))
        except Exception:
            verified = False
    if not user or not verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    reset_rate_limit(rate_limit_key)
    to_encode = {"sub": user.email, "role": user.role}
    access_token = create_access_token(to_encode, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(access_token=access_token)


if ENVIRONMENT in ("prod", "production"):
    GOOGLE_CLIENT_ID = os.getenv("PROD_GOOGLE_OAUTH_CLIENT_ID", "")
else:
    GOOGLE_CLIENT_ID = os.getenv("DEV_GOOGLE_OAUTH_CLIENT_ID", "")


@router.post("/google", response_model=Token)
def google_auth(payload: GoogleAuthRequest, request: Request, db: Session = Depends(get_db)):
    """Verify a Google ID token (credential from Sign In With Google) and return a JWT."""
    client_host = request.client.host if request.client else "unknown"
    # 20 attempts / 5 minutes per client — bounds hammering of the outbound
    # Google tokeninfo call; a forged/expired credential can't be brute-forced
    # the way a password can, so this is DoS/abuse protection more than
    # credential-stuffing defense.
    check_rate_limit(f"google:{client_host}", max_attempts=20, window_seconds=300)
    try:
        r = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": payload.credential},
            timeout=10,
        )
        r.raise_for_status()
        info = r.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Token Google invalide")

    # Validate audience when GOOGLE_CLIENT_ID is configured
    if GOOGLE_CLIENT_ID and info.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Token Google invalide (audience)")

    google_id: str = info.get("sub", "")
    email: str = info.get("email", "")
    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Token Google incomplet")

    # Google's tokeninfo returns email_verified as the string "true"/"false" (or a
    # bool). We MUST require a verified email before linking to or creating an account
    # by email: otherwise anyone who controls a Google account with an *unverified*
    # email equal to a victim's registered email would be issued a JWT for the
    # victim's account (account takeover).
    email_verified_raw = info.get("email_verified")
    email_verified = str(email_verified_raw).strip().lower() == "true" or email_verified_raw is True
    if not email_verified:
        raise HTTPException(status_code=400, detail="Email Google non vérifié")

    # Find existing user by google_id, then by email (link account)
    user = crud_user.get_user_by_google_id(db, google_id)
    if user is None:
        user = crud_user.get_user_by_email(db, email)
        if user is not None:
            user = crud_user.link_google_id(db, user, google_id)
        else:
            prenom = info.get("given_name") or email.split("@")[0]
            nom = info.get("family_name") or ""
            user = crud_user.create_oauth_user(db, google_id=google_id, email=email, prenom=prenom, nom=nom)

    to_encode = {"sub": user.email, "role": user.role}
    access_token = create_access_token(to_encode, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(access_token=access_token)
