from fastapi import APIRouter, Depends

from backend.app.core import experiment
from backend.app.core.concurrency import analysis_slot
from backend.app.core.security import require_api_key
from backend.app.schemas.request_schema import FeedbackRequest, TextRequest, UrlRequest
from backend.app.schemas.response_schema import (
    CacheClearResponse,
    CacheStatsResponse,
    ContentAnalysisResponse,
    ErrorResponse,
    ExperimentStatusResponse,
    FeedbackResponse,
    FeedbackStatsResponse,
    PredictResponse,
)
from backend.app.services import feedback_store
from backend.app.services.content_classifier_service import ContentClassifierService
from backend.app.services.phishing_service import PhishingService
from backend.app.utils import url_cache

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
    responses={
        500: {"model": ErrorResponse, "description": "Error interno no controlado"},
        503: {"model": ErrorResponse, "description": "Cola de análisis saturada"},
    },
)
def predict(request: UrlRequest):
    with analysis_slot():
        return PhishingService.analyze(request.url)


@router.post(
    "/analyze-content",
    response_model=ContentAnalysisResponse,
    tags=["Análisis"],
    summary="Clasificar texto libre (REAL/FAKE)",
    description="Textos con menos de 300 caracteres devuelven verdict='no_content' sin clasificar.",
    responses={
        500: {"model": ErrorResponse, "description": "Error interno no controlado"},
        503: {"model": ErrorResponse, "description": "Cola de análisis saturada"},
    },
)
def analyze_content(request: TextRequest):
    with analysis_slot():
        return ContentClassifierService.analyze(request.text)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["Feedback"],
    summary="Reportar un veredicto incorrecto",
    description=(
        "Registra una corrección del usuario para reentrenar el scoring. "
        "La URL se persiste hasheada (SHA-256), nunca en claro."
    ),
    responses={500: {"model": ErrorResponse, "description": "Error interno no controlado"}},
)
def submit_feedback(request: FeedbackRequest):
    recorded = feedback_store.record(
        url=request.url,
        predicted_risk=request.predicted_risk,
        predicted_score=request.predicted_score,
        reported_risk=request.reported_risk,
        confidence=request.confidence,
        variant=request.variant,
    )
    return {"recorded": recorded, "total": feedback_store.stats()["total"]}


@router.get(
    "/feedback/stats",
    response_model=FeedbackStatsResponse,
    tags=["Feedback"],
    summary="Resumen de correcciones acumuladas",
    description=(
        "Falsos positivos (predijimos HIGH, el usuario reporta LOW) y falsos "
        "negativos (predijimos LOW, el usuario reporta HIGH) se cuentan por "
        "separado: sus costes son distintos."
    ),
)
def feedback_stats():
    return feedback_store.stats()


@router.get(
    "/experiment/status",
    response_model=ExperimentStatusResponse,
    tags=["Feedback"],
    summary="Configuración activa del experimento de scoring",
    description=(
        "Requiere autenticación: el reparto de tráfico entre variantes es "
        "configuración interna y no se publica en /metadata."
    ),
)
def experiment_status():
    return experiment.status()


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
