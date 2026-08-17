# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI Phishing Detector: a FastAPI backend + Chrome extension (Manifest V3) that analyzes URLs for phishing risk using a multi-signal ML pipeline (URL/HTML features, WHOIS, three threat-intel APIs, and three ML models).

## Commands

All commands run from the repo root. The venv is at `venv/`.

**Run the backend:**
```powershell
venv\Scripts\uvicorn backend.app.main:app --reload
```
Serves at `http://localhost:8000`.

**Run the full test suite** (`pyproject.toml`'s `[tool.pytest.ini_options]` sets `testpaths = ["tests", "backend/tests"]`):
```powershell
venv\Scripts\python -m pytest
```

**Lint** (`pyproject.toml`'s `[tool.ruff]`/`[tool.ruff.lint]`: line-length 100, py312, rules `E,F,I,B`; `scripts/generate_*.py` are exempted from `E501` since their long lines are narrative report/diagram content, not logic):
```powershell
venv\Scripts\python -m ruff check .
```

**Run a single test file:**
```powershell
venv\Scripts\python -m pytest backend/tests/test_risk_engine.py -v
```

`tests/conftest.py` patches `backend.app.random_forest.model_loader` and `backend.app.roberta.model_loader` in `sys.modules` **before** any backend code is imported, so the full test suite runs without real `.pkl`/HF model files present. Tests importing `backend.app.main` (e.g. `tests/test_content_api.py`) get this for free as long as conftest loads first (default pytest behavior). It also defines an `autouse` fixture that clears `RateLimitMiddleware`'s `_rate_store` before every test — the limiter buckets by IP only (not by path), so without the reset, tests hitting `/predict`/`/analyze-content` in sequence would trip 429s from earlier tests.

**Quick model smoke test (Random Forest):**
```powershell
venv\Scripts\python -m backend.app.random_forest.test_predict
```

**Train Random Forest** (requires `datasets/raw/phishing_urls.csv`, saves `random_forest_v2.pkl` + `feature_columns_v2.pkl` to `models/`):
```powershell
venv\Scripts\python training/train_random_forest.py
```

**Train RoBERTa URL classifier** (requires `datasets/roberta_dataset.csv`, saves to `models/roberta_phishing_new`):
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

`models/` is not versioned (`.gitignore`); `datasets/raw/phishing_urls.csv` is versioned. Without `random_forest_v2.pkl` or `roberta_phishing_new/`, those signals fail in a controlled way (`_safe()` in `phishing_service.py` returns `{"error": ...}` instead of crashing the pipeline). Without `models/roberta_content/`, `ContentClassifierService` falls back to the HuggingFace hub model `hamzab/roberta-fake-news-classification`.

## Architecture

### Analysis pipeline (`POST /predict`)

`PhishingService.analyze` runs in two parallel waves, then sequentially:

1. **Group 1 (parallel, 6 workers):** URL feature extraction is CPU-only and runs before the wave. Then in parallel: WHOIS domain info, HTML fetch+parse, VirusTotal API, Google Safe Browsing API, Fact Check API, RoBERTa URL classifier.

2. **Group 2:** depends on the HTML result — Random Forest (mapped features).

3. **Sequential:** FusionEngine combines RF + RoBERTa URL scores (40/60 weighted), then `RiskEngine.calculate` aggregates all signals into a 0–100 score with human-readable reasons, returning `LOW/MEDIUM/HIGH` risk. `content_classification` is always `None` in the `/predict` response — content classification only happens via the separate `/analyze-content` endpoint, it's not part of the URL pipeline fusion.

Results are cached in-memory (TTL 10 min, max 500 entries) keyed by URL.

### API security (`backend/app/core/`)

- `config.py` loads `.env` into a `settings` singleton: `virustotal_api_key`, `safe_browsing_api_key`, `fact_check_api_key`, `api_key` (backend auth, empty = disabled), `allowed_origins` (comma-separated extra CORS origins).
- `security.py` — `require_api_key` is a FastAPI dependency applied to the whole router in `routes.py` (`APIRouter(dependencies=[Depends(require_api_key)])`). It reads the `X-API-Key` header; if `settings.api_key` is empty the check is a no-op (auth disabled), otherwise the header must match exactly or it 403s.
- `settings.environment` (`ENVIRONMENT` env var, default `development`) — if set to `production` with no `API_KEY` configured, `main.py` raises `RuntimeError` at startup instead of booting an unauthenticated backend.
- `main.py` also registers a custom `RateLimitMiddleware`: 30 requests/60s per client IP, scoped to `/predict` and `/analyze-content` only, returns 429 with `Retry-After: 60` when exceeded (keyed by IP only, not by path — the two endpoints share one bucket). The in-memory `_rate_store` is bounded to 10,000 distinct IPs (`_RATE_MAX_IPS`), evicting the oldest entry once full, so it can't grow unbounded from one-off/spoofed IPs. It also registers `RequestLoggingMiddleware`, which logs method/path/status/latency/IP for every request.
- `require_api_key` compares the `X-API-Key` header with `hmac.compare_digest`, not `==`, to avoid a timing side-channel on the key comparison.
- CORS (`main.py`) uses `allow_origin_regex` (not a static list) to accept any `chrome-extension://` origin plus `localhost`/`127.0.0.1`, extended with `settings.allowed_origins` if set.
- A global `@app.exception_handler(Exception)` in `main.py` catches unhandled errors, logs the traceback, and returns a 500 with `{"error": ..., "detail": ...}` — `detail` is omitted when `settings.environment == "production"` to avoid leaking internals.

### ML models

| File | Used by | Versioning |
|---|---|---|
| `random_forest_v2.pkl` | `RandomForestPredictor` — predicts phishing from 34 URL/HTML features | HuggingFace Hub |
| `feature_columns_v2.pkl` | column order for the RF model | HuggingFace Hub |
| `roberta_phishing_new/` | `RobertaPredictor` — fine-tuned `distilroberta-base` on URL strings | HuggingFace Hub |
| `roberta_content/` | `ContentClassifierService` — FAKE/REAL news classifier (falls back to `hamzab/roberta-fake-news-classification` if dir missing) | HuggingFace Hub |

All three loaders resolve this directory via `get_models_dir()` in `backend/app/core/paths.py`, which defaults to `<repo root>/models` and can be overridden with the `MODELS_DIR` env var (used by the Docker deployment, see "Deployment" below). Model files are versioned on HuggingFace Hub and downloaded/cached on first use.

### External APIs (env vars in `.env`)

- `VIRUSTOTAL_API_KEY` — VirusTotal v3
- `SAFE_BROWSING_API_KEY` — Google Safe Browsing v4
- `FACT_CHECK_API_KEY` — Google Fact Check Tools API
- `API_KEY` — backend's own auth key, checked against the `X-API-Key` request header (empty disables auth)
- `ALLOWED_ORIGINS` — extra CORS origins beyond the built-in chrome-extension/localhost regex
- `MODELS_DIR` — overrides where model loaders look for `models/` (read directly via `os.getenv` in `backend/app/core/paths.py`, not through the `settings` singleton); defaults to `<repo root>/models`, set to `/models` in the Docker deployment

### All endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/predict` | Full URL analysis pipeline, returns cached result if available |
| `POST` | `/analyze-content` | Raw text only → `ContentClassifierService` (REAL/FAKE); texts under 300 chars return a `no_content`/`UNKNOWN` verdict rather than being classified |
| `GET` | `/health` | Liveness check used by the extension's connection test |
| `GET` | `/` | Root sanity check |
| `GET` | `/metadata` | API version, which ML model files are present on disk, and active rate-limit/cache config |
| `GET` | `/cache/stats` | Cache hit/miss stats and entry count |
| `DELETE` | `/cache` | Evict all cached results |
| `GET` | `/metrics` | Prometheus scrape endpoint (request/latency metrics + startup duration), not in the OpenAPI schema — see "Monitoring" below |

The whole router (including `/predict`, `/analyze-content`, and the cache endpoints) sits behind `require_api_key`; only `/`, `/health`, `/metadata`, and `/metrics` (all defined directly on `app` in `main.py`) are unauthenticated. Every endpoint has a typed Pydantic `response_model` from `backend/app/schemas/response_schema.py` for the OpenAPI/Swagger contract, except `/metrics` (plain-text Prometheus exposition format, added by `prometheus-fastapi-instrumentator`, excluded from the schema via `include_in_schema=False`). Full request/response contract with curl examples: `docs/api.md`.

### Chrome extension (`extension/`)

Manifest V3. The backend URL defaults to `http://localhost:8000` and is configurable via the options page (stored in `chrome.storage.sync`). If `API_KEY` is set on the backend, the extension's options page must also be given that key so `services/api_client.js` can send it as `X-API-Key`.

`background.js` only sets `openPanelOnActionClick: false` on install — it does **not** auto-analyze tabs. Analysis is always user-initiated.

Two UIs share `services/api_client.js`:
- **Popup** (`popup/`) — compact gauge wheel, URL-only analysis
- **Sidebar** (`sidebar/`) — richer panel with two tabs: URL analysis (verdict, ML model bars, threat intel) and Content analysis (calls `POST /analyze-content` with pasted text)

`content.js` is a placeholder reserved for future in-page banner injection.


### Module layout

```
backend/app/
  api/routes.py          # FastAPI router (behind require_api_key), 2 analysis endpoints + cache ops
  main.py                # App entry, CORS, RateLimitMiddleware, RequestLoggingMiddleware, global exception handler, /, /health, /metadata
  core/
    config.py            # Loads .env into a settings singleton (API keys, backend api_key, allowed_origins)
    security.py          # require_api_key dependency (X-API-Key header check)
  services/
    phishing_service.py  # Orchestrates the full pipeline
    risk_engine.py        # Score aggregator (rule-based, 0-100)
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
    domain_utils.py       # WHOIS wrapper
    feature_mapper.py     # Maps url+html features → RF input dict
    url_cache.py          # Thread-safe in-memory TTL cache
  schemas/
    request_schema.py     # UrlRequest (validates http/https prefix), TextRequest
    response_schema.py     # response_model for every endpoint (OpenAPI contract), incl. MetadataResponse, ErrorResponse
    ml_response.py         # MLPredictionResponse pydantic model

backend/tests/            # Unit tests (url_features, html_features, feature_mapper, risk_engine, html_analyzer, content_classifier)
tests/                    # Root-level tests + conftest.py (model-loader mocks shared by both test dirs)

training/                  # Random Forest training pipeline (separate from backend/app/roberta/)
  train_random_forest.py   # requires datasets/raw/phishing_urls.csv → models/random_forest_v2.pkl
  preprocess.py, create_roberta_dataset.py, check_roberta_dataset.py

scripts/
  run_training.py             # CLI: CSV(url,body,label) → train → evaluate (phishing_detector/)
  test_phishing_url.py         # ad-hoc single-URL check against phishing_detector/
  augment_roberta_dataset.py    # dataset augmentation for the RoBERTa URL trainer

docs/                      # api.md, architecture.md, decision_tree.md, mvp_scope.md, testing_report.md, user_stories.md, changelog.md, presentacion.md
```

## Key conventions

- `RiskEngine` starts every URL at a score of **50** and applies positive/negative deltas from each signal. Final range is clamped to 0–100; ≥80 = LOW risk, ≥50 = MEDIUM, <50 = HIGH.
- `_safe(fn, *args)` in `phishing_service.py` wraps every parallel call; a failed sub-service returns `{"error": "..."}` and never crashes the pipeline.
- All three model loaders (`random_forest/model_loader.py`, `roberta/model_loader.py`, `ContentClassifierService`) are lazy and download from HuggingFace Hub on first call — load via `@lru_cache`-wrapped `get_model()` on first call, not at import time. Downloaded models are cached locally in `./models`. If internet is unavailable or HuggingFace is unreachable, that signal fails via `_safe()` and doesn't crash the app.
- `FusionEngine` gracefully degrades: if one model errors, it uses the other at full weight.
- `ContentClassifierService` is lazy-loaded (via `@lru_cache`) on first call; uses HuggingFace model `hamzab/roberta-fake-news-classification` by default. Inputs under 300 characters short-circuit to a `no_content`/`UNKNOWN`/`0.0` result rather than being run through the model.
- Label normalization in `ContentClassifierService`: model returns `TRUE/FALSE`, normalized to `REAL/FAKE`.
- The Random Forest expects exactly the columns in `feature_columns_v2.pkl`; `FeatureMapper.map` must produce those keys (missing ones default to 0).
- `HtmlFetcher.get_html` (`backend/app/analyzers/html_fetcher.py`) has SSRF protections since the URL it fetches is caller-controlled via `/predict`: only `http`/`https` schemes, each hostname is resolved and rejected if any of its IPs is private/loopback/link-local/reserved/multicast/unspecified (blocks localhost, RFC1918, and cloud metadata endpoints like `169.254.169.254`), redirects are followed manually (max 5 hops) with the same host check re-applied on every hop, and the response body is capped at 2 MB. Any change to how the backend fetches attacker-controlled URLs must preserve these checks.
- The Random Forest's label convention is `0 = phishing, 1 = legitimate`; `RandomForestPredictor` must map `predict_proba` accordingly (`phishing_probability` from class 0, `legitimate_probability` from class 1) — these were previously inverted, silently biasing 40% of the fusion score, so treat this mapping as load-bearing when touching `random_forest/predictor.py`.
- `get_domain_info` passes `timeout=10` to `whois.whois()` so a slow/unresponsive WHOIS server can't hang the whole `/predict` request.
- The extension (`popup.js`, `sidebar.js`) builds history and reason-list DOM nodes via safe DOM APIs (`createElement`/`textContent`), not by interpolating URLs or `RiskEngine` reason strings into `innerHTML` — both are attacker-influenceable (the analyzed URL, and text scraped from the analyzed page).
- When adding new backend tests, put them under `backend/tests/` (not a new top-level dir) so `pyproject.toml`'s `testpaths` and the shared `conftest.py` model mocks pick them up automatically.

## 📚 Full Documentation

- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — Pipeline flowchart, RiskEngine scoring, ML models, Chrome extension
- **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)** — Step-by-step Render deployment, env vars, troubleshooting
- **[`docs/TESTING.md`](docs/TESTING.md)** — Test audit results, new test coverage, running tests locally
- **[`docs/API.md`](docs/API.md)** — Endpoint reference with curl examples
- **[`docs/changelog.md`](docs/changelog.md)** — Recent changes and versions

---

## Deployment (Render, Docker)

**→ See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for complete step-by-step guide.**

Quick summary:
- Set **Dockerfile path** to `backend/Dockerfile` (Render doesn't auto-detect)
- Configure env vars: `VIRUSTOTAL_API_KEY`, `SAFE_BROWSING_API_KEY`, `FACT_CHECK_API_KEY`, `API_KEY` (opt), `FORWARDED_ALLOW_IPS=*`, `ENVIRONMENT`
- Models download from HuggingFace Hub during build (~60-90s cold start)
- Enable Auto-Deploy on push to `main`
- Service at `https://<service-name>.onrender.com`

## Monitoring (Prometheus + Grafana, local only)

Local visibility via `docker-compose.yml` (not deployed to Render):
- `GET /metrics` exposes Prometheus metrics: `http_requests_total`, latency histograms, `app_startup_duration_seconds`
- `docker compose up -d backend prometheus grafana` starts stack with auto-provisioned dashboard
- Grafana at `http://localhost:3000`, Prometheus at `http://localhost:9090`

## Testing

✅ **281 tests passing** — Unit + integration tests with 100% model mocking (no real model files needed).

**→ See [`docs/TESTING.md`](docs/TESTING.md) for test strategy and audit results (49 new tests added 2026-08-17).**

Key tests:
- SSRF guard (34): IP validation, DNS-rebinding prevention
- Rate limiting (7): Proxy headers, bucketing, eviction
- Security (8): Error filtering, no internals leaking
- Full pipeline (200+): URL features, HTML analysis, fusion, risk scoring

## CI (`.github/workflows/ci.yml`)

Runs on push/PR to `main`: checkout → Python 3.12 → `pip install -r requirements-dev.txt --extra-index-url https://download.pytorch.org/whl/cpu` → `ruff check .` → `pytest -v`.

- `requirements-dev.txt` = `backend/requirements.txt` (CPU torch) + pinned `pytest`/`ruff` — deliberately *not* the root `requirements.txt`, which pins `torch==...+cu128` and would fail to resolve on a GPU-less GitHub Actions runner.
- The `--extra-index-url` flag is required for the `+cpu` torch wheel to resolve; without it, `pip install` fails with "No matching distribution found".
- No model files or `.env` secrets are needed for CI — `tests/conftest.py` mocks the RF/RoBERTa loaders before import, so the whole suite runs against the same mocks used locally.
