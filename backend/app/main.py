import re
import time
import logging
import threading
from collections import defaultdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.core.paths import get_models_dir
from backend.app.utils import url_cache
from backend.app.schemas.response_schema import (
    HealthResponse,
    RootResponse,
    MetadataResponse,
)

logger = logging.getLogger("phishing_api")

# Falla rápido si el backend se despliega en producción sin autenticación.
if settings.environment == "production" and not settings.api_key:
    raise RuntimeError(
        "ENVIRONMENT=production requiere API_KEY configurada en .env "
        "(ver backend/app/core/security.py — sin ella, /predict y /analyze-content "
        "quedan sin autenticación)."
    )

# ── Rate limiting ────────────────────────────────────────────────────────────
_RATE_WINDOW = 60   # segundos
_RATE_MAX    = 30   # solicitudes por ventana por IP

_rate_store: dict = defaultdict(list)
_rate_lock  = threading.Lock()

_RATE_LIMITED_PATHS = {"/predict", "/analyze-content"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _RATE_LIMITED_PATHS:
            return await call_next(request)

        ip  = request.client.host if request.client else "unknown"
        now = time.time()

        with _rate_lock:
            _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
            if len(_rate_store[ip]) >= _RATE_MAX:
                return JSONResponse(
                    {"error": "Demasiadas solicitudes. Intenta de nuevo en 1 minuto."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            _rate_store[ip].append(now)

        return await call_next(request)


# ── Logging de requests ─────────────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)
        ip = request.client.host if request.client else "unknown"
        logger.info(
            "%s %s %s %sms ip=%s",
            request.method, request.url.path, response.status_code, elapsed_ms, ip,
        )
        return response


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Phishing Detector",
    version="1.0.0",
    openapi_tags=[
        {"name": "Sistema", "description": "Liveness y sanity checks, sin autenticación."},
        {"name": "Análisis", "description": "Pipeline de detección de phishing y clasificación de contenido."},
        {"name": "Cache", "description": "Inspección y limpieza del cache en memoria."},
    ],
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Permite: extensiones Chrome (cualquier ID), localhost y 127.0.0.1,
# más orígenes adicionales configurados en ALLOWED_ORIGINS.
_origin_regex = r"chrome-extension://[a-z]{32}|http://(localhost|127\.0\.0\.1)(:\d+)?"
if settings.allowed_origins:
    _extra = "|".join(re.escape(o) for o in settings.allowed_origins)
    _origin_regex = f"{_origin_regex}|{_extra}"

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=_origin_regex,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(router)


# ── Manejo controlado de errores no previstos ────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    detail = str(exc) if settings.environment != "production" else None
    return JSONResponse(
        {"error": "Error interno del servidor", "detail": detail},
        status_code=500,
    )


@app.get("/", response_model=RootResponse, tags=["Sistema"], summary="Sanity check")
def root():
    return {"message": "AI Phishing Detector Running"}


@app.get("/health", response_model=HealthResponse, tags=["Sistema"], summary="Liveness check")
def health():
    return {"status": "healthy"}


@app.get(
    "/metadata",
    response_model=MetadataResponse,
    tags=["Sistema"],
    summary="Version, modelos disponibles y configuración activa",
)
def metadata():
    models_dir = get_models_dir()
    cache_info = url_cache.stats()
    return {
        "api_version": app.version,
        "models": {
            "random_forest": (models_dir / "random_forest_v2.pkl").exists()
            and (models_dir / "feature_columns_v2.pkl").exists(),
            "roberta_url": (models_dir / "roberta_phishing_new").exists(),
            "roberta_content": (models_dir / "roberta_content" / "config.json").exists(),
        },
        "rate_limit_per_minute": _RATE_MAX,
        "cache_ttl_seconds": cache_info["ttl_seconds"],
        "cache_max_size": cache_info["max_size"],
    }
