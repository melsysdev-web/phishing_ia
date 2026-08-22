import logging
import re
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.core import concurrency, logging_config, torch_config
from backend.app.core.config import settings
from backend.app.core.model_warmup import warmup_models
from backend.app.core.paths import get_models_dir

# Lo primero: sin esto el root logger no tiene handlers y todo lo que registre
# el proyecto se descarta en silencio. Va antes que el resto del arranque para
# que los avisos de configuración y de carga de modelos ya se vean.
logging_config.configure()

# Debe ejecutarse antes de que cualquier import transitivo cargue un modelo
# torch (routes -> phishing_service -> roberta/model_loader) — los loaders son
# lazy, pero set_num_interop_threads solo puede llamarse una vez, antes de que
# arranque trabajo paralelo, así que se hace lo antes posible en el arranque.
torch_config.configure()

from backend.app.api.routes import router  # noqa: E402
from backend.app.schemas.response_schema import (  # noqa: E402
    DobleResponse,
    HealthResponse,
    MetadataResponse,
    RootResponse,
)
from backend.app.utils import url_cache  # noqa: E402

logger = logging.getLogger("phishing_api")

# Referencia de "arranque": desde que uvicorn importa este módulo hasta que el
# startup de FastAPI termina (incluye wiring de middlewares y router,
# no la carga de modelos ML — esos son lazy, ver core del pipeline).
_process_start_time = time.time()

app_startup_seconds = Gauge(
    "app_startup_duration_seconds",
    "Tiempo desde el import del módulo hasta que FastAPI termina su startup",
)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    # Identifica qué se está ejecutando realmente. Un despliegue de Render solo
    # se puede verificar por el log y por /predict: /metadata dice qué ficheros
    # de modelo existen en disco, no si la inferencia cabe en memoria.
    logger.info(
        "Arranque: version=%s environment=%s models_dir=%s",
        app.version, settings.environment, get_models_dir(),
    )
    # No se publica en /metadata (endpoint sin autenticar): saber que solo cabe
    # un análisis a la vez le ahorra el trabajo a quien quiera saturarlo. En el
    # log de arranque queda visible para verificar un despliegue.
    logger.info("Límite de análisis simultáneos: %s", concurrency.status())
    # Warm up ML models on startup to prevent OOM on concurrent requests
    warmup_models()
    app_startup_seconds.set(time.time() - _process_start_time)
    yield

def verify_auth_config(cfg) -> None:
    """Aborta el arranque si producción quedó sin autenticación por descuido.

    El caso deliberado existe y hay que permitirlo: la extensión se publica en
    una tienda, y un paquete descargable no puede guardar un secreto, así que
    exigirle una clave solo daría una falsa sensación de control. Se declara con
    ALLOW_UNAUTHENTICATED.

    Lo que no vale es esquivar la comprobación quitando ENVIRONMENT=production:
    eso arrastraría consigo el filtrado de internals en las respuestas de error,
    que no tiene nada que ver con la autenticación.
    """
    if cfg.environment != "production" or cfg.api_key:
        return

    if not cfg.allow_unauthenticated:
        raise RuntimeError(
            "ENVIRONMENT=production requiere API_KEY configurada en .env "
            "(ver backend/app/core/security.py — sin ella, /predict y /analyze-content "
            "quedan sin autenticación). Si la exposición pública es intencionada, "
            "declara ALLOW_UNAUTHENTICATED=true."
        )

    # A nivel WARNING y en cada arranque: una API pública puede ser una decisión
    # válida, pero nunca debe pasar inadvertida al leer los logs.
    logger.warning(
        "API pública: /predict y /analyze-content aceptan peticiones sin autenticar "
        "(ALLOW_UNAUTHENTICATED). Las defensas activas son el límite por IP, el "
        "circuit breaker de cuota y el guardián de SSRF."
    )


verify_auth_config(settings)

# ── Rate limiting ────────────────────────────────────────────────────────────
_RATE_WINDOW   = 60     # segundos
_RATE_MAX      = 30     # solicitudes por ventana por IP
_RATE_MAX_IPS  = 10_000  # límite de IPs distintas rastreadas (evita fuga de memoria)

_rate_store: dict = {}
_rate_lock  = threading.Lock()

_RATE_LIMITED_PATHS = {"/predict", "/analyze-content"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _RATE_LIMITED_PATHS:
            return await call_next(request)

        ip  = request.client.host if request.client else "unknown"
        now = time.time()

        with _rate_lock:
            recent = [t for t in _rate_store.get(ip, []) if now - t < _RATE_WINDOW]
            if len(recent) >= _RATE_MAX:
                _rate_store[ip] = recent
                return JSONResponse(
                    {"error": "Demasiadas solicitudes. Intenta de nuevo en 1 minuto."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            recent.append(now)

            if ip not in _rate_store and len(_rate_store) >= _RATE_MAX_IPS:
                oldest_ip = min(_rate_store, key=lambda k: max(_rate_store[k], default=0))
                del _rate_store[oldest_ip]

            _rate_store[ip] = recent

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
    lifespan=_lifespan,
    openapi_tags=[
        {"name": "Sistema", "description": "Liveness y sanity checks, sin autenticación."},
        {
            "name": "Análisis",
            "description": "Pipeline de detección de phishing y clasificación de contenido.",
        },
        {"name": "Cache", "description": "Inspección y limpieza del cache en memoria."},
        {
            "name": "Debug",
            "description": (
                "Endpoints de prueba sin relación con el producto — "
                "no forman parte del contrato de la API."
            ),
        },
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

# instrument() se llama después de registrar los demás middlewares para que
# quede como el más externo del stack y mida la latencia total de la request
# (CORS + rate limit + logging + endpoint), no solo el tiempo del handler.
# expose() publica /metrics sin autenticación (igual que /health y /metadata)
# para que Prometheus pueda scrapearlo sin necesitar X-API-Key.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


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


@app.get(
    "/doble/{numero}",
    response_model=DobleResponse,
    tags=["Debug"],
    summary="Duplicar un número (endpoint de prueba)",
    description=(
        "Sin relación con el pipeline de phishing — solo para verificar "
        "que el routing y la validación de parámetros funcionan."
    ),
)
def doble(numero: int):
    return {"numero": numero, "doble": numero * 2}
