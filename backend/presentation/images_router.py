from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from presentation.deps import get_current_user
from services.image_service import download_image

router = APIRouter(prefix="/images", tags=["images"])


class ImageFetchIn(BaseModel):
    url: str


@router.post("/fetch")
def fetch_image(payload: ImageFetchIn, request: Request, _current_user=Depends(get_current_user)):
    try:
        rel = download_image(payload.url)
        base = str(request.base_url).rstrip('/')
        return {"image_link": f"{base}{rel}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
