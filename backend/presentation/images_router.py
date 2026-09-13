from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from presentation.deps import AdminUser
from services.image_service import download_image
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
