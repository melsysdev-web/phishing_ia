from fastapi import FastAPI

app = FastAPI(
    title="AI Phishing Detector",
    version="1.0.0"
)

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