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


class TextRequest(BaseModel):
    text: str = Field(
        ...,
        description=(
            "Texto libre a clasificar. Menos de 300 caracteres responde "
            "verdict='no_content' sin ejecutar el modelo (umbral aplicado en "
            "ContentClassifierService, no en este schema)."
        ),
    )