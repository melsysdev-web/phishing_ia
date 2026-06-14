# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Start the backend server:**
```
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Run all tests:**
```
pytest
```

**Run a single test file:**
```
pytest tests/test_risk_engine.py
```

**Run a specific test:**
```
pytest tests/test_risk_engine.py::test_function_name
```

Dependencies are managed via `requirements.txt`. Install with:
```
pip install -r requirements.txt
```

## Architecture

This is an AI-powered phishing detection system consisting of two parts: a **FastAPI backend** and a **Chrome extension** frontend.

### Request Flow (`POST /predict`)

`PhishingService.analyze()` orchestrates two parallel groups, then a sequential phase:

1. **Group 1 (parallel, 6 threads):** `get_domain_info`, `HtmlAnalyzer.analyze`, `VirusTotalService.analyze`, `SafeBrowsingService.analyze`, `FactCheckService.analyze`, `RobertaPredictor.predict` — all independent.
2. **Group 2 (parallel, 2 threads, depends on Group 1):** `RandomForestPredictor.predict` (needs HTML features via `FeatureMapper`) and `ContentClassifierService.analyze` (needs `page_text` from HTML).
3. **Sequential:** `FusionEngine.combine(rf, roberta)` → `RiskEngine.calculate(...)` → final response.

Results are cached in `url_cache` to avoid re-analyzing the same URL.

### ML Layer

Two models run in parallel and are merged by a weighted fusion:

- **RoBERTa URL classifier** (`models/roberta_phishing/`): Fine-tuned `roberta-base` that classifies URLs directly as phishing/legitimate. Weight: 0.6. Loaded at module import time from `backend/app/roberta/model_loader.py`.
- **Random Forest** (`models/random_forest_v2.pkl`): Trained on structured features (URL + HTML). Weight: 0.4. Features assembled by `FeatureMapper`.
- **FusionEngine** (`backend/app/ml/fusion/fusion_engine.py`): Weighted average of both `phishing_probability` values. Falls back to the surviving model if one fails.

### Content Classifier (separate endpoint)

`POST /analyze-content` uses `ContentClassifierService`, which runs a separate RoBERTa pipeline (`hamzab/roberta-fake-news-classification`) on page text to detect misinformation. Falls back from local model (`models/roberta_content/`) to the HuggingFace remote if the local `config.json` is absent.

### RiskEngine

`backend/app/services/risk_engine.py` scores 0–100 starting at 50, applying weighted bonuses/penalties from:
- URL structural features (HTTPS, IP usage, `@` symbol, subdomain count, URL length, suspicious keywords)
- Domain age and TLD
- HTML features (password fields, hidden fields, no title/favicon, excessive JS)
- VirusTotal verdict
- Google Safe Browsing verdict
- Fact Check API verdict
- Content classification label+confidence
- ML fusion `phishing_probability`

Score ≥ 80 → LOW risk, ≥ 50 → MEDIUM, < 50 → HIGH.

### External APIs

Configured via `.env` (loaded via `python-dotenv`):
- `VIRUSTOTAL_API_KEY` — VirusTotal URL reputation
- `SAFE_BROWSING_API_KEY` — Google Safe Browsing
- `FACT_CHECK_API_KEY` — Google Fact Check Tools API

### Chrome Extension

Located in `extension/`. Manifest V3 service worker. The popup has two tabs:
- **URL tab**: auto-analyzes the active tab's URL via `ApiClient.analyze(url)` → `POST /predict`
- **Content tab**: lets the user paste text for manual classification via `ApiClient.analyzeContent(text)` → `POST /analyze-content`

Backend must be running on `localhost:8000`. The extension has no build step — load `extension/` as an unpacked extension in Chrome.

### Testing

`tests/conftest.py` patches `backend.app.random_forest.model_loader` and `backend.app.roberta.model_loader` via `sys.modules` before any imports, so tests never load actual model files. All test files share fixtures defined in `conftest.py` (safe/phishing URL feature dicts, domain info, sample HTML).

### Key files

| Path | Role |
|------|------|
| `backend/app/services/phishing_service.py` | Main orchestrator |
| `backend/app/services/risk_engine.py` | Scoring logic |
| `backend/app/ml/fusion/fusion_engine.py` | RF + RoBERTa merger |
| `backend/app/roberta/predictor.py` | RoBERTa URL inference |
| `backend/app/services/content_classifier_service.py` | Fake-news classifier |
| `backend/app/utils/feature_mapper.py` | URL+HTML → RF feature vector |
| `backend/app/api/routes.py` | API route definitions |
| `extension/popup/popup.js` | Extension UI logic |
| `extension/services/api_client.js` | Extension ↔ backend HTTP client |
| `tests/conftest.py` | ML model mocks + shared fixtures |
