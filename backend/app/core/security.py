import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from backend.app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(_api_key_header)):
    if not settings.api_key:
        return
    if not key or not hmac.compare_digest(key, settings.api_key):
        raise HTTPException(status_code=403, detail="API key inválida o ausente")
