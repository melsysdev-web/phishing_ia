from fastapi import FastAPI

from backend.app.api.routes import router

app = FastAPI(
    title="AI Phishing Detector",
    version="1.0.0"
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "AI Phishing Detector Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }