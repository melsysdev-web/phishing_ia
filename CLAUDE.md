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

**Train standalone phishing classifier** (custom RoBERTa + classifier head, requires a CSV with `url,body,label` columns; saves to `checkpoints/phishing_detector/best_model.pt`):
```powershell
venv\Scripts\python scripts\run_training.py datasets\mi_dataset.csv
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

### All endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/predict` | Full URL analysis pipeline, returns cached result if available |
| `POST` | `/analyze-content` | Raw text only → `ContentClassifierService` (REAL/FAKE) |
| `GET` | `/health` | Liveness check used by the extension's connection test |
| `GET` | `/cache/stats` | Cache hit/miss stats and entry count |
| `DELETE` | `/cache` | Evict all cached results |

### Chrome extension (`extension/`)

Manifest V3. The backend URL defaults to `http://localhost:8000` and is configurable via the options page (stored in `chrome.storage.sync`).

`background.js` only sets `openPanelOnActionClick: false` on install — it does **not** auto-analyze tabs. Analysis is always user-initiated.

Two UIs share `services/api_client.js`:
- **Popup** (`popup/`) — compact gauge wheel, URL-only analysis
- **Sidebar** (`sidebar/`) — richer panel with two tabs: URL analysis (verdict, ML model bars, threat intel) and Content analysis (calls `POST /analyze-content` with pasted text)

`content.js` is a placeholder reserved for future in-page banner injection.

### Standalone fine-tuning module (`phishing_detector/`)

Independent from `backend/app/roberta/` — built around a custom classifier head (not `AutoModelForSequenceClassification`) for full control over the training loop. **Not yet wired into `PhishingService`** — it's a standalone library + CLI for experimenting with a from-scratch fine-tune.

- `model.py` — `PhishingClassifier`: `roberta-base` encoder → pooler `[CLS]` output (768) → `Dropout→Linear(256)→ReLU→Dropout→Linear(2)`. `freeze_encoder()` / `unfreeze_last_n_layers(n)` support gradual fine-tuning.
- `preprocess.py` — `normalize_url()` decodes percent-encoding and expands hex/octal/decimal IP literals (e.g. `0x7f000001` → `127.0.0.1`); `prepare_input(url, body)` produces `"[URL] {url} [BODY] {text}"`.
- `dataset.py` — `PhishingDataset` tokenizes the entire text list once in `__init__` (batched), not per-`__getitem__`.
- `train.py` — `train()`: AdamW + linear warmup (10% of steps) + early stopping (patience 3 on `val_loss`); always returns the model restored to its **best** checkpoint, not the last epoch's weights.
- `predict.py` — `predict_single`/`predict_batch`; model+tokenizer are lazy-loaded once via `@lru_cache`, mirroring `ContentClassifierService`'s pattern. `predict_single` is a thin wrapper over `predict_batch`.
- `evaluate.py` — `evaluate_model()` returns precision/recall/F1/AUC-ROC.
- `scripts/run_training.py` — end-to-end CLI: validates CSV columns (`url,body,label`), splits stratified by label, trains, evaluates.

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
    ml_response.py       # MLPredictionResponse pydantic model
  core/
    config.py            # Loads API keys from .env into a settings singleton

phishing_detector/        # standalone module, see above — not wired into backend/
  config.py              # MAX_LENGTH, BATCH_SIZE, LEARNING_RATE, etc.
  model.py                # PhishingClassifier (RoBERTa + custom head)
  preprocess.py            # normalize_url, clean_text, prepare_input
  dataset.py                # PhishingDataset (batched tokenization)
  train.py                   # AdamW + warmup + early stopping
  predict.py                  # predict_single / predict_batch (lazy-loaded)
  evaluate.py                  # precision/recall/F1/AUC-ROC

scripts/
  run_training.py             # CLI: CSV(url,body,label) → train → evaluate
```

## Key conventions

- `RiskEngine` starts every URL at a score of **50** and applies positive/negative deltas from each signal. Final range is clamped to 0–100; ≥80 = LOW risk, ≥50 = MEDIUM, <50 = HIGH.
- `_safe(fn, *args)` in `phishing_service.py` wraps every parallel call; a failed sub-service returns `{"error": "..."}` and never crashes the pipeline.
- `FusionEngine` gracefully degrades: if one model errors, it uses the other at full weight.
- `ContentClassifierService` is lazy-loaded (via `@lru_cache`) on first call; uses local model dir if `models/roberta_content/config.json` exists, else HuggingFace hub.
- Label normalization in `ContentClassifierService`: remote model returns `TRUE/FALSE`, local returns `REAL/FAKE` — both are normalized to `REAL/FAKE`.
- The Random Forest expects exactly the columns in `feature_columns_v2.pkl`; `FeatureMapper.map` must produce those keys (missing ones default to 0).
