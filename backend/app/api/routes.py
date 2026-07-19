from fastapi import APIRouter, Depends

from backend.app.schemas.request_schema import UrlRequest, TextRequest
from backend.app.schemas.response_schema import (
    PredictResponse,
    ContentAnalysisResponse,
    CacheStatsResponse,
    CacheClearResponse,
    ErrorResponse,
)
from backend.app.services.phishing_service import PhishingService
from backend.app.services.content_classifier_service import ContentClassifierService
from backend.app.utils import url_cache
from backend.app.core.security import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post(
    "/predict",
    response_model=PredictResponse,
    tags=["Análisis"],
    summary="Analizar una URL",
    description=(
        "Pipeline completo: WHOIS, HTML, VirusTotal, Safe Browsing, Fact Check, "
        "Random Forest y RoBERTa fusionados en un score 0-100. Resultado cacheado 10 min."
    ),
    responses={500: {"model": ErrorResponse, "description": "Error interno no controlado"}},
)
def predict(request: UrlRequest):
    return PhishingService.analyze(request.url)


@router.post(
    "/analyze-content",
    response_model=ContentAnalysisResponse,
    tags=["Análisis"],
    summary="Clasificar texto libre (REAL/FAKE)",
    description="Textos con menos de 300 caracteres devuelven verdict='no_content' sin clasificar.",
    responses={500: {"model": ErrorResponse, "description": "Error interno no controlado"}},
)
def analyze_content(request: TextRequest):
    return ContentClassifierService.analyze(request.text)


@router.get(
    "/cache/stats",
    response_model=CacheStatsResponse,
    tags=["Cache"],
    summary="Estadísticas del cache en memoria",
)
def cache_stats():
    return url_cache.stats()


@router.delete(
    "/cache",
    response_model=CacheClearResponse,
    tags=["Cache"],
    summary="Vaciar el cache en memoria",
)
def cache_clear():
    n = url_cache.clear()
    return {"cleared": n}
