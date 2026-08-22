import os

from dotenv import load_dotenv

load_dotenv()


class _Settings:
    virustotal_api_key:    str       = os.getenv("VIRUSTOTAL_API_KEY", "")
    safe_browsing_api_key: str       = os.getenv("SAFE_BROWSING_API_KEY", "")
    fact_check_api_key:    str       = os.getenv("FACT_CHECK_API_KEY", "")
    api_key:               str       = os.getenv("API_KEY", "")
    environment:           str       = os.getenv("ENVIRONMENT", "development")
    # Reconoce explícitamente que el backend se expone sin autenticación.
    # Sin esto, arrancar en producción sin API_KEY es un error: casi siempre
    # es un despiste, no una decisión. Aquí sí es una decisión — la extensión
    # se publica en una tienda y no puede llevar un secreto de verdad.
    allow_unauthenticated: bool      = os.getenv("ALLOW_UNAUTHENTICATED", "").strip().lower() in {
        "1", "true", "yes", "si", "sí",
    }
    allowed_origins:       list[str] = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]


settings = _Settings()
