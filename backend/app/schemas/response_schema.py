from pydantic import BaseModel


class UrlResponse(BaseModel):
    url: str
    features: dict