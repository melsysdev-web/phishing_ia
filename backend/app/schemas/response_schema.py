from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class Interval(BaseModel):
    lower: float
    upper: float


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="allow")

    risk: Optional[str] = None
    score: Optional[int] = None
    reasons: list[str] = []
    # Calibración: probabilidad de phishing e incertidumbre asociada.
    # Opcionales porque el cache warm persiste 30 días: tras un deploy siguen
    # sirviéndose entradas escritas por la versión anterior, sin estos campos.
    probability: Optional[float] = None
    probability_interval: Optional[Interval] = None
    confidence: Optional[float] = None
    score_interval: Optional[Interval] = None
    ml_agreement: Optional[float] = None
    num_signals: Optional[int] = None


class PredictResponse(BaseModel):
    # Sub-diccionarios tipados como dict: cada señal puede degradarse a
    # {"error": "..."} si su sub-servicio falla (ver _safe() en phishing_service.py).
    model_config = ConfigDict(extra="allow")

    url: str
    cached: bool
    analysis_time_ms: Optional[int] = None
    # Ausente en entradas cacheadas por versiones previas al experimento.
    scoring_variant: Optional[str] = None
    risk_assessment: RiskAssessment
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


class FeedbackResponse(BaseModel):
    recorded: bool
    total: int


class ExperimentStatusResponse(BaseModel):
    enabled: bool
    rollout: float
    variant: str
    control: str


class FeedbackStatsResponse(BaseModel):
    total: int
    false_positives: int
    false_negatives: int
    by_predicted_risk: dict


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


class DobleResponse(BaseModel):
    numero: int
    doble: int
