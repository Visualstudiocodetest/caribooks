from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from presentation.deps import AdminUser
from services.image_service import download_image, save_uploaded_image
from services.rate_limit import check_rate_limit

router = APIRouter(prefix="/images", tags=["images"])


class ImageFetchIn(BaseModel):
    url: str


@router.post("/fetch")
def fetch_image(payload: ImageFetchIn, request: Request, admin: AdminUser):
    # Even though this is admin-gated, a compromised/malicious admin session
    # could otherwise use it to rapidly probe internal network ranges (the
    # SSRF allowlist blocks the request, but response timing/error differences
    # still leak port-scan-style information) -- bound the rate like the other
    # sensitive endpoints in auth_router.py.
    check_rate_limit(f"images_fetch:{admin.id_utilisateur}", max_attempts=20, window_seconds=300)
    try:
        rel = download_image(payload.url)
        base = str(request.base_url).rstrip('/')
        return {"image_link": f"{base}{rel}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/upload")
async def upload_image(request: Request, admin: AdminUser, file: UploadFile = File(...)):
    """Store a photo taken/picked directly in the browser (eg. a picture of a
    book's cover) as the book's image -- the fallback path for when OpenLibrary
    has no cover art, or the ISBN lookup fails outright."""
    check_rate_limit(f"images_upload:{admin.id_utilisateur}", max_attempts=20, window_seconds=300)
    data = await file.read()
    try:
        rel = save_uploaded_image(data, file.content_type or "")
        base = str(request.base_url).rstrip('/')
        return {"image_link": f"{base}{rel}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
