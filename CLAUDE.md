# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI Phishing Detector: a FastAPI backend + Chrome extension (Manifest V3) that analyzes URLs for phishing risk using a multi-signal ML pipeline.

## Commands

All commands run from the repo root. The venv is at `venv/`.

**Run the backend:**
```powershell
venv\Scripts\uvicorn backend.app.main:app --reload
```

**Run a single test file:**
```powershell
venv\Scripts\python -m pytest backend/app/analyzers/test_html_analyzer.py -v
```

**Quick model smoke test (Random Forest):**
```powershell
venv\Scripts\python -m backend.app.random_forest.test_predict
```

**Train RoBERTa URL classifier** (requires `datasets/roberta_dataset.csv`, saves to `models/roberta_phishing`):
```powershell
venv\Scripts\python backend/app/roberta/trainer.py
```

**Train content classifier (fake news / REAL-FAKE)** (downloads `GonzaloA/fake_news` from HuggingFace, saves to `models/roberta_content`):
```powershell
venv\Scripts\python backend/app/roberta/content_trainer.py
```

**Spanish content trainer** (same purpose, Spanish dataset):
```powershell
venv\Scripts\python backend/app/roberta/content_trainer_es.py
```

## Architecture

### Analysis pipeline (`POST /predict`)

`PhishingService.analyze` runs in two parallel waves, then sequentially:

1. **Group 1 (parallel, 6 workers):** URL feature extraction is CPU-only and runs before the wave. Then in parallel: WHOIS domain info, HTML fetch+parse, VirusTotal API, Google Safe Browsing API, Fact Check API, RoBERTa URL classifier.

2. **Group 2 (parallel, 2 workers):** depends on HTML result — Random Forest (mapped features) and ContentClassifierService (page text).

3. **Sequential:** FusionEngine combines RF + RoBERTa URL scores (40/60 weighted), then RiskEngine aggregates all signals into a 0–100 score with human-readable reasons, returning `LOW/MEDIUM/HIGH` risk.

Results are cached in-memory (TTL 10 min, max 500 entries) keyed by URL.

### ML models (`models/`)

| File | Used by |
|---|---|
| `random_forest_v2.pkl` | `RandomForestPredictor` — predicts phishing from 18 URL/HTML features |
| `feature_columns_v2.pkl` | column order for the RF model |
| `roberta_phishing/` | `RobertaPredictor` — fine-tuned `distilroberta-base` on URL strings |
| `roberta_content/` | `ContentClassifierService` — FAKE/REAL news classifier (falls back to `hamzab/roberta-fake-news-classification` if dir missing) |

### External APIs (env vars in `.env`)

- `VIRUSTOTAL_API_KEY` — VirusTotal v3
- `SAFE_BROWSING_API_KEY` — Google Safe Browsing v4
- `FACT_CHECK_API_KEY` — Google Fact Check Tools API

### Second endpoint (`POST /analyze-content`)

Accepts raw text, runs only `ContentClassifierService`. Used independently from the URL pipeline.

### Chrome extension (`extension/`)

Manifest V3. `background.js` triggers on tab update, calls `POST /predict` via `services/api_client.js`, and the result is rendered in `popup/popup.html` with a three-state UI (safe / suspicious / dangerous).

### Module layout

```
backend/app/
  api/routes.py          # FastAPI router (2 endpoints + cache ops)
  main.py                # App entry, CORS
  services/
    phishing_service.py  # Orchestrates the full pipeline
    risk_engine.py       # Score aggregator (rule-based, 0–100)
    content_classifier_service.py
    virustotal_service.py
    safe_browsing_service.py
    fact_check_service.py
  ml/fusion/fusion_engine.py  # Weighted RF+RoBERTa combiner
  random_forest/         # RF model loader, predictor, trainer
  roberta/               # RoBERTa URL model; content trainers
  analyzers/             # HTML fetch (html_fetcher) + feature extraction (html_features, html_analyzer)
  utils/
    url_features.py      # URL string feature extraction
    domain_utils.py      # WHOIS wrapper
    feature_mapper.py    # Maps url+html features → RF input dict
    url_cache.py         # Thread-safe in-memory TTL cache
  schemas/
    request_schema.py    # UrlRequest (validates http/https prefix), TextRequest
```

## Key conventions

- `_safe(fn, *args)` in `phishing_service.py` wraps every parallel call; a failed sub-service returns `{"error": "..."}` and never crashes the pipeline.
- `FusionEngine` gracefully degrades: if one model errors, it uses the other at full weight.
- `ContentClassifierService` is lazy-loaded (via `@lru_cache`) on first call; uses local model dir if `models/roberta_content/config.json` exists, else HuggingFace hub.
- Label normalization in `ContentClassifierService`: remote model returns `TRUE/FALSE`, local returns `REAL/FAKE` — both are normalized to `REAL/FAKE`.
- The Random Forest expects exactly the columns in `feature_columns_v2.pkl`; `FeatureMapper.map` must produce those keys (missing ones default to 0).
