import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from presentation.book_router import router as book_router
from presentation.auth_router import router as auth_router
from presentation.catalog_router import router as catalog_router
from presentation.article_router import router as article_router
from presentation.stock_router import router as stock_router
from presentation.order_router import router as order_router
from presentation.scan_router import router as scan_router
from presentation.user_router import router as user_router
from presentation.images_router import router as images_router
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI()

default_origins = ",".join([
    "https://plobooks.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
])
origins_env = os.getenv("FRONTEND_ORIGINS", default_origins)
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    # This endpoint can be used by load balancers or monitoring tools to check if the application is running.
    return {"status": "ok",
            "code": 200, 
            "message": "Health check passed"}

app.include_router(book_router)
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(article_router)
app.include_router(stock_router)
app.include_router(order_router)
app.include_router(scan_router)
app.include_router(user_router)
app.include_router(images_router)

# Serve static files (images, uploaded files) using an absolute path so imports
# don't depend on the current working directory when tests run.
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")