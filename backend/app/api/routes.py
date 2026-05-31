from fastapi import APIRouter

from backend.app.schemas.request_schema import UrlRequest
from backend.app.services.phishing_service import PhishingService

router = APIRouter()


@router.post("/predict")
def predict(request: UrlRequest):
    return PhishingService.analyze(
        request.url
    )