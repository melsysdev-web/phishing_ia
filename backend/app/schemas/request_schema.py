from pydantic import BaseModel, Field, field_validator


class UrlRequest(BaseModel):
    url: str = Field(..., description="URL a analizar. Debe comenzar con http:// o https://")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("La URL debe comenzar con http:// o https://")
        return v


class FeedbackRequest(BaseModel):
    url: str = Field(..., description="URL analizada. Se persiste hasheada, nunca en claro.")
    predicted_risk: str = Field(..., description="Veredicto que devolvió el backend")
    predicted_score: int = Field(..., ge=0, le=100, description="Score devuelto (0-100)")
    reported_risk: str = Field(..., description="Veredicto correcto según el usuario")
    confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Confianza reportada en el análisis original"
    )
    variant: str | None = Field(None, description="Variante de scoring que produjo el veredicto")

    @field_validator("predicted_risk", "reported_risk")
    @classmethod
    def validate_risk(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError("El veredicto debe ser LOW, MEDIUM o HIGH")
        return v


class TextRequest(BaseModel):
    text: str = Field(
        ...,
        description=(
            "Texto libre a clasificar. Menos de 300 caracteres responde "
            "verdict='no_content' sin ejecutar el modelo (umbral aplicado en "
            "ContentClassifierService, no en este schema)."
        ),
    )