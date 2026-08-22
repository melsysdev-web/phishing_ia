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

`tests/conftest.py` patches `backend.app.random_forest.model_loader` and `backend.app.roberta.model_loader` in `sys.modules` **before** any backend code is imported, so the full test suite runs without real `.pkl`/HF model files present. Tests importing `backend.app.main` (e.g. `tests/test_content_api.py`) get this for free as long as conftest loads first (default pytest behavior). It also defines `autouse` fixtures that:
- Clear `RateLimitMiddleware`'s `_rate_store` before every test — the limiter buckets by IP only (not by path), so without the reset, tests hitting `/predict`/`/analyze-content` in sequence would trip 429s from earlier tests.
- Reset VirusTotal quota circuit breaker state before every test to prevent state leakage between tests (the circuit is global and affects all VT service calls).

**Check /predict still fits in Render's 512 MB** (needs Docker; builds the production image, so the first run downloads ~821 MB of weights):
```powershell
venv\Scripts\python scripts\memory_check.py --concurrency 2
```
Fails if the kernel OOM-kills the container. Deliberately not in CI — the image build is too heavy for a per-PR job.

**Package the extension for the store** (never zip `extension/` by hand — the manifest must land at the ZIP root, and the 1.0.4 package shipped broken because it didn't):
```powershell
.\scripts\package_extension.ps1
```
Validates the manifest's file references, that `config.js` is present, that `BACKEND_DEFAULT_URL` is not localhost and is declared in `host_permissions`, and that the auth model is coherent (`BACKEND_IS_PUBLIC` vs `BACKEND_DEFAULT_API_KEY`). Refuses to emit a ZIP if any check fails, then re-verifies the built archive and deletes it if `manifest.json`/`config.js` aren't at the root.

**Verify a deployment** (`/health` and `/metadata` do *not* verify one — see "Memory budget" below):
```powershell
venv\Scripts\python scripts\smoke_test.py --base-url https://<service>.onrender.com
```

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
- `settings.environment` (`ENVIRONMENT` env var, default `development`) — if set to `production` with no `API_KEY` configured, `verify_auth_config()` in `main.py` raises `RuntimeError` at startup instead of booting an unauthenticated backend. The deliberate case is allowed but must be declared: `ALLOW_UNAUTHENTICATED=true` lets it boot and logs a WARNING on every startup. This deployment runs that way on purpose — a store-distributed extension cannot hold a secret, so the defences are the per-IP rate limit, the VirusTotal quota circuit breaker and the SSRF guard. Do **not** work around the check by dropping `ENVIRONMENT=production`: that also re-enables the `detail` field in error responses, which is unrelated to auth.
- `main.py` also registers a custom `RateLimitMiddleware`: 30 requests/60s per client IP, scoped to `/predict` and `/analyze-content` only, returns 429 with `Retry-After: 60` when exceeded (keyed by IP only, not by path — the two endpoints share one bucket). The in-memory `_rate_store` is bounded to 10,000 distinct IPs (`_RATE_MAX_IPS`), evicting the oldest entry once full, so it can't grow unbounded from one-off/spoofed IPs. It also registers `RequestLoggingMiddleware`, which logs method/path/status/latency/IP for every request.
- `require_api_key` compares the `X-API-Key` header with `hmac.compare_digest`, not `==`, to avoid a timing side-channel on the key comparison.
- CORS (`main.py`) uses `allow_origin_regex` (not a static list) to accept any `chrome-extension://` origin plus `localhost`/`127.0.0.1`, extended with `settings.allowed_origins` if set.
- A global `@app.exception_handler(Exception)` in `main.py` catches unhandled errors, logs the traceback, and returns a 500 with `{"error": ..., "detail": ...}` — `detail` is omitted when `settings.environment == "production"` to avoid leaking internals.

### ML models

| File | Used by | Where the weights live |
|---|---|---|
| `random_forest_v2.pkl` | `RandomForestPredictor` — predicts phishing from 34 URL/HTML features | HuggingFace Hub |
| `feature_columns_v2.pkl` | column order for the RF model | HuggingFace Hub |
| `roberta_phishing_new/` | `RobertaPredictor` — fine-tuned `distilroberta-base` on URL strings | HuggingFace Hub |
| `roberta_content/` | `ContentClassifierService` — FAKE/REAL news classifier (falls back to `hamzab/roberta-fake-news-classification` if dir missing) | HuggingFace Hub |

All three loaders resolve this directory via `get_models_dir()` in `backend/app/core/paths.py`, which defaults to `<repo root>/models` and can be overridden with the `MODELS_DIR` env var (used by the Docker deployment, see "Deployment" below).

The weights are versioned on HuggingFace Hub (`mel3601/phishing-ia-models`), but **the loaders do not download them**: `random_forest/model_loader.py` calls `joblib.load` on a local path and `roberta/model_loader.py` calls `from_pretrained` on a local directory. The download happens once in `backend/Dockerfile` at *build* time via `snapshot_download`, baking the weights into the image. Locally you must supply `models/` yourself — copy it, pull it from the Hub, or retrain. The one runtime download is `ContentClassifierService`, which falls back to the hub id `hamzab/roberta-fake-news-classification` when `models/roberta_content/` is absent.

### External APIs (env vars in `.env`)

- `VIRUSTOTAL_API_KEY` — VirusTotal v3
- `SAFE_BROWSING_API_KEY` — Google Safe Browsing v4
- `FACT_CHECK_API_KEY` — Google Fact Check Tools API
- `API_KEY` — backend's own auth key, checked against the `X-API-Key` request header (empty disables auth)
- `ALLOWED_ORIGINS` — extra CORS origins beyond the built-in chrome-extension/localhost regex
- `ALLOW_UNAUTHENTICATED` — set to `true` to declare a deliberately public backend; without it, `ENVIRONMENT=production` with an empty `API_KEY` aborts startup
- `EXPERIMENT_ROLLOUT` — fraction of traffic (0.0–1.0) routed to the candidate scoring variant; `0.0`/unset/out-of-range disables the experiment
- `EXPERIMENT_VARIANT` — name reported for the candidate variant (default `candidate`)
- `MAX_CONCURRENT_ANALYSES` — analyses allowed at once across `/predict` + `/analyze-content` (default `1`); above 1 on a 512 MB instance the worker gets OOM-killed, see "Memory budget" below
- `ANALYSIS_QUEUE_TIMEOUT` — seconds a queued analysis waits before giving up with 503 (default `30`)
- `LOG_LEVEL` — root log level (default `INFO`); an unrecognised value falls back to `INFO` rather than leaving the service silent
- `MODELS_DIR` — overrides where model loaders look for `models/` (read directly via `os.getenv` in `backend/app/core/paths.py`, not through the `settings` singleton); defaults to `<repo root>/models`, set to `/models` in the Docker deployment

### All endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/predict` | Full URL analysis pipeline, returns cached result if available |
| `POST` | `/analyze-content` | Raw text only → `ContentClassifierService` (REAL/FAKE); texts under 300 chars return a `no_content`/`UNKNOWN` verdict rather than being classified |
| `POST` | `/feedback` | Record a user correction of a verdict (URL stored SHA-256 hashed, never in clear) |
| `GET` | `/feedback/stats` | Accumulated corrections, with false positives and false negatives counted separately |
| `GET` | `/experiment/status` | Active scoring-experiment config (authenticated: traffic split is not published on `/metadata`) |
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

docs/                      # Base del proyecto: mvp_scope.md, user_stories.md, decision_tree.md,
                           #   testing_report.md, presentacion.md
                           # Referencia técnica: api.md, architecture.md, changelog.md,
                           #   DEPLOYMENT.md, TESTING.md, EXTENSION_STABILITY.md
                           # Publicación: EDGE_ADDON_UPLOAD.md, EDGE_STORE_DESCRIPTIONS.md
```

## Key conventions

- `RiskEngine` starts every URL at a score of **50** and applies positive/negative deltas from each signal. Final range is clamped to 0–100; ≥80 = LOW risk, ≥50 = MEDIUM, <50 = HIGH.
- `RiskEngine` also returns calibration fields (`probability`, `probability_interval`, `confidence`, `score_interval`, `ml_agreement`, `num_signals`) via `confidence_calibration.py`. `confidence` is a **0–1 float** — it used to be an int equal to `score`, which conflated two concepts. These fields are `Optional` in `RiskAssessment` because the 30-day warm cache keeps serving entries written before they existed.
- The hyphen penalty reads `num_hyphens_domain` (hostname only), not `num_hyphens` (whole URL). Counting the whole URL penalized any news/docs page with a long slug while letting `paypal-secure-login-verify.com` through. `num_hyphens` is kept unchanged because the Random Forest consumes it as `NumHyphens` and was trained on that distribution — redefining it would silently shift the model's inputs.
- Dynamic delta scaling: the young-domain penalty is multiplied by `_YOUNG_DOMAIN_DAMPING` when VirusTotal *and* Safe Browsing both report clean, since legitimate newly-registered sites are the main false-positive source. A confirmed threat never triggers damping.
- Signals inside `RiskEngine.calculate` are `[delta, text, kind]` lists (mutable) so the damping pass can rewrite them; `kind` tags the signals eligible for contextual scaling.
- `feedback_store.py` hashes URLs with SHA-256 before persisting — the backend learns from corrections without recording which sites a user visits. Write failures are swallowed: a lost correction must not break the analysis the user asked for.
- `experiment.assign()` is deterministic by URL hash. Non-deterministic assignment would let the same URL return different verdicts, and the cache (which does not key on variant) would serve whichever landed first. Rollout defaults to 0.0, so the experiment is inert until `EXPERIMENT_ROLLOUT` is set.
- `_safe(fn, *args)` in `phishing_service.py` wraps every parallel call; a failed sub-service returns `{"error": "..."}` and never crashes the pipeline.
- All three model loaders (`random_forest/model_loader.py`, `roberta/model_loader.py`, `ContentClassifierService`) are lazy: they load via an `@lru_cache`-wrapped `get_model()` on first call, not at import time. They read from `get_models_dir()` on disk — they do **not** fetch from HuggingFace Hub (the Dockerfile does that at build time). The exception is `ContentClassifierService`, which passes a hub id when the local directory is missing and therefore does download at runtime. A missing or unreadable model fails via `_safe()` and doesn't crash the app.
- `warmup_models()` (`backend/app/core/model_warmup.py`) loads nothing — it logs a line and returns. Loading is lazy in every environment, via the `@lru_cache`'d `get_model()` of each loader, so the first `/predict` after a restart pays ~30-60s. It does **not** branch on `ENVIRONMENT`; the name is a leftover from when it did, and eager warmup was removed because it OOM-killed the worker on Render's 512 MB.
- `FusionEngine` gracefully degrades: if one model errors, it uses the other at full weight.
- `ContentClassifierService` is lazy-loaded (via `@lru_cache`) on first call; uses HuggingFace model `hamzab/roberta-fake-news-classification` by default. Inputs under 300 characters short-circuit to a `no_content`/`UNKNOWN`/`0.0` result rather than being run through the model.
- Label normalization in `ContentClassifierService`: model returns `TRUE/FALSE`, normalized to `REAL/FAKE`.
- The Random Forest expects exactly the columns in `feature_columns_v2.pkl`; `FeatureMapper.map` must produce those keys (missing ones default to 0).
- `HtmlFetcher.get_html` (`backend/app/analyzers/html_fetcher.py`) has SSRF protections since the URL it fetches is caller-controlled via `/predict`: only `http`/`https` schemes, each hostname is resolved and rejected if any of its IPs is private/loopback/link-local/reserved/multicast/unspecified (blocks localhost, RFC1918, and cloud metadata endpoints like `169.254.169.254`), redirects are followed manually (max 5 hops) with the same host check re-applied on every hop, and the response body is capped at 2 MB. Any change to how the backend fetches attacker-controlled URLs must preserve these checks.
- The Random Forest's label convention is `0 = phishing, 1 = legitimate`; `RandomForestPredictor` must map `predict_proba` accordingly (`phishing_probability` from class 0, `legitimate_probability` from class 1) — these were previously inverted, silently biasing 40% of the fusion score, so treat this mapping as load-bearing when touching `random_forest/predictor.py`.
- `get_domain_info` passes `timeout=10` to `whois.whois()` so a slow/unresponsive WHOIS server can't hang the whole `/predict` request.
- The extension (`popup.js`, `sidebar.js`) builds history and reason-list DOM nodes via safe DOM APIs (`createElement`/`textContent`), not by interpolating URLs or `RiskEngine` reason strings into `innerHTML` — both are attacker-influenceable (the analyzed URL, and text scraped from the analyzed page).
- When adding new backend tests, put them under `backend/tests/` (not a new top-level dir) so `pyproject.toml`'s `testpaths` and the shared `conftest.py` model mocks pick them up automatically.

## Git Workflow

**All changes must go through feature branches — NEVER commit directly to main.**

1. Create branch: `git checkout -b fix/issue-name` or `feature/issue-name`
2. Make changes and commit locally
3. Push to remote: `git push origin branch-name`
4. Create PR for review
5. Merge via PR after approval

This ensures all changes are tested in CI before landing on main.

## 📚 Full Documentation

**Project basis** — what the project set out to do and how it is judged. Keep these in sync when behaviour changes:

- **[`docs/mvp_scope.md`](docs/mvp_scope.md)** — Scope, objectives, what is in and out
- **[`docs/user_stories.md`](docs/user_stories.md)** — User stories with acceptance criteria
- **[`docs/decision_tree.md`](docs/decision_tree.md)** — Every RiskEngine delta, the damping rules and the calibrated output. **Update this whenever a score delta changes.**
- **[`docs/testing_report.md`](docs/testing_report.md)** — Manual test cases plus what the automated suite covers
- **[`docs/presentacion.md`](docs/presentacion.md)** — Project presentation and FAQ

**Technical reference:**

- **[`docs/architecture.md`](docs/architecture.md)** — Pipeline flowchart, RiskEngine scoring, ML models, Chrome extension
- **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)** — Step-by-step Render deployment, env vars, troubleshooting
- **[`docs/TESTING.md`](docs/TESTING.md)** — Test audit results, new test coverage, running tests locally
- **[`docs/api.md`](docs/api.md)** — Endpoint reference with curl examples
- **[`docs/EXTENSION_STABILITY.md`](docs/EXTENSION_STABILITY.md)** — Defensive code in the extension and the failures it absorbs
- **[`SCORE_IMPROVEMENTS_STRATEGY.md`](SCORE_IMPROVEMENTS_STRATEGY.md)** — What the scoring work delivered, and what is blocked on labelled data
- **[`docs/changelog.md`](docs/changelog.md)** — Recent changes and versions

---

## Deployment (Render, Docker)

**→ See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for complete step-by-step guide.**

Quick summary:
- Set **Dockerfile path** to `backend/Dockerfile` (Render doesn't auto-detect)
- Configure env vars:
  - `VIRUSTOTAL_API_KEY`, `SAFE_BROWSING_API_KEY`, `FACT_CHECK_API_KEY` — threat-intel APIs
  - `API_KEY` (optional) — backend authentication key
  - `ENVIRONMENT` — `production` or `development`. Does **not** affect model loading (always lazy). In `production` the backend refuses to start without `API_KEY` unless `ALLOW_UNAUTHENTICATED=true` is set, and error responses omit the `detail` field so internals don't leak
  - `ALLOW_UNAUTHENTICATED` — declares an intentionally public backend, so `production` boots without `API_KEY`. Must stay in sync with `BACKEND_IS_PUBLIC` in `extension/config.js`
  - `FORWARDED_ALLOW_IPS=*` — allow X-Forwarded-For from Render's proxy
- Models download from HuggingFace Hub during build (~60-90s cold start); lazy loading on first request in production
- Enable Auto-Deploy on push to `main`
- Service at `https://<service-name>.onrender.com`

### Memory budget — why `/predict` was returning 502

Model distribution is solved: the Dockerfile downloads the weights from `mel3601/phishing-ia-models` on Hugging Face during build and bakes them into the image at `/models` (`MODELS_DIR=/models`). That is why `/metadata` sees them.

The failure was **RAM at inference time**, not distribution. Measured RSS per stage (local CUDA torch build; the Docker CPU wheel is smaller, but the per-model deltas hold):

| Stage | Δ RSS |
|---|---|
| `import torch` | +470 MB (CUDA build; CPU wheel is materially smaller) |
| `import transformers` + `fastapi` | +33 MB |
| Random Forest (300 trees, depth 29, 321k nodes) | +156 MB |
| RoBERTa URL, **with** `quantize_dynamic` | **+538 MB** (757 MB peak) |
| RoBERTa URL, **without** quantization | **+115 MB** |

`roberta_content` is *not* loaded by `/predict` — only `/analyze-content` touches it.

**The int8 quantization was the cause.** It was added to speed up CPU inference, but to convert the weights it materializes all of them, spiking +735 MB, whereas safetensors otherwise maps the fp32 weights lazily. It bought 1.96 ms/URL (16.5%) in a pipeline that takes 3–8 s dominated by network I/O. Removing it cut `/predict` from 1213 MB to 791 MB. `torch.ao.quantization` is also deprecated and removed in torch 2.10. **Do not reintroduce it** — see the note in `roberta/model_loader.py`.

Disabling warmup earlier did not fix the 502; it moved the allocation from startup to the first `/predict`, where the single worker (`WEB_CONCURRENCY=1`) was OOM-killed and took the whole service down with it.

**`/metadata` reporting `"models": true` is not evidence that inference works** — it only calls `.exists()` on the files. Verifying a deployment requires calling `/predict`.

Remaining gap: after the fix the non-torch footprint is ~320 MB; whether that plus the CPU torch wheel fits in 512 MB has not been measured on Render itself. If it still does not fit, the levers are a larger instance, or retraining the Random Forest with fewer than 300 trees (needs validation data to justify the accuracy tradeoff).

## Monitoring (Prometheus + Grafana, local only)

Local visibility via `docker-compose.yml` (not deployed to Render):
- `GET /metrics` exposes Prometheus metrics: `http_requests_total`, latency histograms, `app_startup_duration_seconds`
- `docker compose up -d backend prometheus grafana` starts stack with auto-provisioned dashboard
- Grafana at `http://localhost:3000`, Prometheus at `http://localhost:9090`

## Testing

✅ **535 tests passing** — Unit + integration tests with 100% model mocking (no real model files needed).

**→ See [`docs/TESTING.md`](docs/TESTING.md) for test strategy and audit results (49 new tests added 2026-08-17).**

Key tests:
- SSRF guard (34): IP validation, DNS-rebinding prevention
- Rate limiting (7): Proxy headers, bucketing, eviction
- VT circuit breaker (9): Quota exhaustion, state reset, graceful degradation
- Security (8): Error filtering, no internals leaking
- Full pipeline (200+): URL features, HTML analysis, fusion, risk scoring

## CI (`.github/workflows/`)

`ci.yml` runs on push/PR to `main`: checkout → Python 3.12 → `pip install -r requirements-dev.txt --extra-index-url https://download.pytorch.org/whl/cpu` → `ruff check .` → `pytest -v`.

- `requirements-dev.txt` = `backend/requirements.txt` (CPU torch) + pinned `pytest`/`ruff` — deliberately *not* the root `requirements.txt`, which pins `torch==...+cu128` and would fail to resolve on a GPU-less GitHub Actions runner.
- The `--extra-index-url` flag is required for the `+cpu` torch wheel to resolve; without it, `pip install` fails with "No matching distribution found".
- No model files or `.env` secrets are needed for CI — `tests/conftest.py` mocks the RF/RoBERTa loaders before import, so the whole suite runs against the same mocks used locally.

`smoke-test.yml` runs after a push to `main` (and on demand) and calls `scripts/smoke_test.py`, which hits the deployed `/predict` and checks the response carries a risk score and an ML prediction. It exists because `/health` and `/metadata` both returned 200 while `/predict` 502'd: `/metadata` only calls `.exists()` on the model files, and the pipeline degrades gracefully, so a backend with no working models still answers a well-formed 200. It needs the `SMOKE_BASE_URL`/`SMOKE_API_KEY` repository secrets and skips with a warning without them; it cannot tell which build Render is serving, so the trustworthy run is the manual one once the deploy is live. The script's validation logic is unit-tested in `backend/tests/test_smoke_test.py` and uses only the standard library, so the job doesn't install torch.
