from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class PredictResponse(BaseModel):
    # Sub-diccionarios tipados como dict: cada señal puede degradarse a
    # {"error": "..."} si su sub-servicio falla (ver _safe() en phishing_service.py).
    model_config = ConfigDict(extra="allow")

    url: str
    cached: bool
    analysis_time_ms: Optional[int] = None
    risk_assessment: dict
    machine_learning: dict
    html_analysis: dict
    url_features: dict
    domain_info: dict
    virustotal: dict
    safe_browsing: dict
    fact_check: dict
    content_classification: Optional[Any] = None


class ContentAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    verdict: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    raw_label: Optional[str] = None
    error: Optional[str] = None


class CacheStatsResponse(BaseModel):
    entries: int
    valid: int
    ttl_seconds: int
    max_size: int


class CacheClearResponse(BaseModel):
    cleared: int


class HealthResponse(BaseModel):
    status: str


class RootResponse(BaseModel):
    message: str


class ModelsAvailability(BaseModel):
    random_forest: bool
    roberta_url: bool
    roberta_content: bool


class MetadataResponse(BaseModel):
    api_version: str
    models: ModelsAvailability
    rate_limit_per_minute: int
    cache_ttl_seconds: int
    cache_max_size: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
