from fastapi import APIRouter

from backend.app.schemas.request_schema import UrlRequest
from backend.app.services.phishing_service import PhishingService
from backend.app.utils import url_cache

router = APIRouter()


@router.post("/predict")
def predict(request: UrlRequest):
    return PhishingService.analyze(request.url)


@router.get("/cache/stats")
def cache_stats():
    return url_cache.stats()


@router.delete("/cache")
def cache_clear():
    n = url_cache.clear()
    return {"cleared": n}
