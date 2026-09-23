import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from presentation.auth_router import router as auth_router
from presentation.book_router import router as book_router
from presentation.catalog_router import router as catalog_router
from presentation.images_router import router as images_router
from presentation.order_admin_router import router as order_admin_router
from presentation.order_router import router as order_router
from presentation.payment_router import router as payment_router
from presentation.scan_router import router as scan_router
from presentation.stock_router import router as stock_router
from presentation.user_router import router as user_router

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# OpenAPI metadata: FastAPI builds the whole Swagger/ReDoc page from this, and
# the tag order below is the order the operations are grouped in the docs.
tags_metadata = [
    {"name": "auth", "description": "Inscription, connexion par mot de passe et Google Sign-In (JWT HS256)."},
    {"name": "users", "description": "Profil de l'utilisateur connecté (RGPD/nLPD : export et effacement) et administration des comptes."},
    {"name": "books", "description": "Catalogue des livres et récupération des métadonnées ISBN via OpenLibrary."},
    {"name": "catalog", "description": "Liste de référence : états d'usure."},
    {
        "name": "stock",
        "description": (
            "Sources de stock et quantités disponibles (réservé aux administrateurs, "
            "à l'exception de /stock/availability qui est l'agrégat public utilisé par la vitrine)."
        ),
    },
    {"name": "scans", "description": "Historique des scans ISBN réalisés en recyclerie."},
    {"name": "orders", "description": "Panier et commandes de l'utilisateur connecté."},
    {"name": "orders-payments", "description": "Paiements PostFinance Checkout et webhooks associés."},
    {"name": "orders-admin", "description": "Suivi et transitions de statut des commandes (réservé aux administrateurs)."},
    {"name": "images", "description": "Récupération et stockage des couvertures distantes (protégé contre le SSRF)."},
    {"name": "system", "description": "Sonde de disponibilité du service."},
]

app = FastAPI(
    title="CARIBOOKS API",
    summary="API de la librairie solidaire en ligne de la recyclerie Caritas.",
    description=(
        "Backend FastAPI de CARIBOOKS : catalogue de livres d'occasion, scan ISBN, "
        "panier, commandes et paiements.\n\n"
        "**Contraintes métier** : toutes les transactions sont libellées en **CHF** et "
        "la livraison est limitée à la **Suisse**.\n\n"
        "L'authentification se fait par **JWT** (schéma `HTTPBearer`) : appelez "
        "`POST /auth/token`, puis renseignez le jeton obtenu via le bouton *Authorize*."
    ),
    version="1.0.0",
    license_info={"name": "MIT", "identifier": "MIT"},
    openapi_tags=tags_metadata,
)

default_origins = ",".join([
    "https://caribooks.vercel.app",
    "https://plobooks.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
])
origins_env = os.getenv("FRONTEND_ORIGINS", default_origins)
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
# allow_credentials=True below means Starlette's CORSMiddleware will never
# collapse "*" into a real wildcard -- it instead reflects whatever Origin the
# browser sent, with credentials allowed, for every request. A FRONTEND_ORIGINS
# misconfiguration containing "*" would silently become "any origin, with
# auth," so refuse to start rather than allow that combination.
if "*" in allow_origins:
    raise RuntimeError(
        "FRONTEND_ORIGINS must not contain '*': combined with allow_credentials=True "
        "this would allow any origin to make authenticated requests."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["system"], summary="Racine du service")
async def root() -> dict[str, str]:
    """Point d'entrée minimal, utile pour vérifier que l'API répond."""
    return {"message": "Hello World"}


@app.get("/health", tags=["system"], summary="Sonde de disponibilité")
async def health() -> dict[str, str | int]:
    """Sonde consommée par le healthcheck du conteneur et par le monitoring."""
    return {"status": "ok",
            "code": 200,
            "message": "Health check passed"}

app.include_router(book_router)
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(stock_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(order_admin_router)
app.include_router(scan_router)
app.include_router(user_router)
app.include_router(images_router)

# Serve static files (images, uploaded files) using an absolute path so imports
# don't depend on the current working directory when tests run.
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")