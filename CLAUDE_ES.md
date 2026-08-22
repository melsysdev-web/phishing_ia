# 🇪🇸 CLAUDE_ES.md

Guía concisa en español para trabajar con este proyecto en Claude Code.

---

## 📌 Descripción del Proyecto

**AI Phishing Detector**: Backend FastAPI + Extensión Chrome (Manifest V3) que detecta URLs maliciosas usando pipeline multi-señal: features URL/HTML, WHOIS, 3 APIs threat-intel (VirusTotal, Safe Browsing, Fact Check), 3 modelos ML (Random Forest, RoBERTa URL, RoBERTa Content).

---

## 🚀 Comandos Principales

**Todos desde `<repo-root>`. Venv en `venv/`.**

```powershell
# Backend
venv\Scripts\uvicorn backend.app.main:app --reload     # http://localhost:8000

# Pruebas
venv\Scripts\python -m pytest                           # Suite completa (535 tests)
venv\Scripts\python -m pytest backend/tests/test_risk_engine.py -v  # Test individual

# Linting
venv\Scripts\python -m ruff check .                     # Line length 100, reglas E,F,I,B

# ML Models
venv\Scripts\python training/train_random_forest.py    # Requiere datasets/raw/phishing_urls.csv
venv\Scripts\python backend/app/roberta/trainer.py     # URL classifier
venv\Scripts\python backend/app/roberta/content_trainer.py  # Content classifier
```

**Notas**:
- `tests/conftest.py` mocka los loaders de ML antes de importar → suite completa sin archivos `.pkl` reales
- `models/` no está versionado (`.gitignore`); modelos descargan de HuggingFace Hub en primer uso
- **Warmup de modelos**: En `ENVIRONMENT=development`, pre-carga modelos al startup. En `ENVIRONMENT=production` (Render), lazy loading en primer request (~30-60s) para evitar OOM en el límite de 512MB
- Fallos de modelos degrada gracefully via `_safe()` wrapper — nunca rompe el pipeline

---

## 🏗️ Arquitectura Resumida

### Pipeline de análisis (`POST /predict`)

1. **Grupo 1 (paralelo)**: URL features, WHOIS, HTML fetch+parse, VirusTotal, Safe Browsing, Fact Check, RoBERTa URL
2. **Grupo 2 (depende HTML)**: Random Forest (34 features)
3. **Secuencial**: FusionEngine (40% RF + 60% RoBERTa) → RiskEngine → score 0-100 + reasons

Cache en memoria: TTL 10 min, máx 500 URLs.

### Endpoints principales

| Endpoint | Función |
|---|---|
| `POST /predict` | Análisis URL completo + caché |
| `POST /analyze-content` | Clasificación fake news/real |
| `GET /health` | Health check (extensión) |
| `GET /metadata` | Versión API + modelos presentes |
| `DELETE /cache` | Limpiar caché |

**Seguridad**: Todos detrás `require_api_key` (header `X-API-Key`, configurable en `backend/app/core/config.py`); con `API_KEY` vacía la comprobación es un no-op, que es como corre el despliegue público. CORS regex para `chrome-extension://` + localhost. Rate limit: 30 req/60s por IP.

### ML Models

| Archivo | Uso |
|---|---|
| `random_forest_v2.pkl` | Predictor RF (34 features) |
| `roberta_phishing_new/` | Clasificador URLs (distilroberta-base) |
| `roberta_content/` | Noticias reales/falsas (fallback: hub model) |

### Seguridad (Anti-SSRF, cargas attacker-controlled)

- `HtmlFetcher`: Solo http/https, IP validation (RFC1918, multicast, link-local bloqueados), max 5 redirects con re-check, response cap 2MB
- `RiskEngine`: Score comienza en 50, deltas +/- de señales, resultado clamped 0-100
- DOM safety: `createElement`/`textContent`, NO interpolación en `innerHTML`

---

## 📋 Convenciones & Normas

- **Score convention**: RF `0=phishing, 1=legit` → mantener mapeo en `predict_proba` (fue invertido, sesgó 40% fusión)
- **Content threshold**: <300 chars → `UNKNOWN` sin clasificar
- **Model loading**: Lazy (`@lru_cache`) en primer call, no en import
- **FusionEngine**: Degrada elegantly si un modelo falla
- **Tests**: Poner en `backend/tests/` (no new top-level dir) para que `conftest.py` mocks + `pyproject.toml` testpaths las recojan
- **Comments**: Solo si el WHY es no-obvious (constraints, workarounds). Sin docstrings multi-línea
- **No early abstractions**: 3 líneas duplicadas better than premature helper

---

## 🌿 Git Workflow

**NUNCA commit directo a main. SIEMPRE usar feature branches.**

1. `git checkout -b fix/issue-name` o `feature/issue-name`
2. Hacer cambios y commit local
3. `git push origin branch-name`
4. Crear PR para review
5. Merge via PR después de aprobación

Esto asegura que todos los cambios pasen CI antes de llegar a main.

---

## 🧪 Testing & CI

✅ **535 tests**: Todos passing

- **Suite**: `pytest` con conftest que:
  - Mocka todos los modelos ML
  - Reseta rate limiter por test
  - Reseta circuit breaker VirusTotal por test (evita state leakage)
- **Linting**: `ruff check .` (line-length 100)
- **CI** (`.github/workflows/ci.yml`): Python 3.12, CPU torch, no secrets needed

---

## 📦 Deployment (Render)

**→ Ver [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) para pasos completos.**

Quick:
- Dockerfile path: `backend/Dockerfile`
- Env vars:
  - `VIRUSTOTAL_API_KEY`, `SAFE_BROWSING_API_KEY`, `FACT_CHECK_API_KEY` — threat-intel APIs
  - `API_KEY` (opt) — autenticación backend. **Vacía en producción a propósito**:
    la extensión se publica en una tienda y no puede guardar un secreto
  - `ALLOW_UNAUTHENTICATED` — declara que el backend público es una decisión;
    sin ella, `ENVIRONMENT=production` sin `API_KEY` aborta el arranque
  - `ENVIRONMENT` — `production` o `development` (controla warmup: lazy en prod, eager en dev)
  - `FORWARDED_ALLOW_IPS=*` — permitir X-Forwarded-For del proxy de Render
- Models descargan HF Hub en build (~60-90s); lazy loading en primer request en producción
- Auto-Deploy en push `main`

---

## 📚 Documentación Completa

- **[CLAUDE.md](CLAUDE.md)** — Guía técnica completa (English)
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — Flowcharts, RiskEngine, modelos
- **[`docs/TESTING.md`](docs/TESTING.md)** — Audit 49 nuevos tests (2026-08-17)
- **[`docs/API.md`](docs/API.md)** — Endpoints + curl examples
- **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)** — Render step-by-step
- **[`docs/changelog.md`](docs/changelog.md)** — Cambios recientes

---

## 🎨 Extensión Chrome (Manifest V3)

**Popup** (`extension/popup/`): Quick URL analysis, gauge animation  
**Sidebar** (`extension/sidebar/`): Detailed results + content tab  
**Services** (`extension/services/`): API client  
**Options** (`extension/options/`): Backend URL + API key config

Sin animaciones: anime.js se cargaba desde un CDN, Manifest V3 prohíbe el código remoto
y la CSP ya lo bloqueaba. Se retiró (2026-08-21); el stub que queda deja las llamadas
a `anime()` inertes y la UI renderiza al instante. La extensión no pide ningún host
salvo su propio backend.

---

## 🔗 Estructura Directorios

```
backend/app/
  api/routes.py           # FastAPI router (2 endpoints)
  main.py                 # Entry, CORS, Rate limit, logging
  core/                   # Config, security, settings
  services/               # Orchestration + threat APIs
  ml/fusion/              # FusionEngine (RF + RoBERTa combo)
  random_forest/          # RF loader, trainer, predictor
  roberta/                # RoBERTa URL + content classifiers
  analyzers/              # HTML fetch + feature extraction
  utils/                  # URL features, WHOIS, mappers
  schemas/                # Request/response Pydantic models
backend/tests/            # Unit + integration tests
tests/                    # Root tests + conftest.py mocks
training/                 # RF training pipeline
scripts/                  # CLI tools (train, evaluate)
docs/                     # Full documentation
extension/                # Chrome extension (Manifest V3)
```

---

## ❓ Preguntas Frecuentes

**¿Dónde están los modelos?**  
`models/` (no versionado). Descargan HF Hub en primer acceso. Sin archivos → señal falla, pipeline sigue.

**¿Por qué tests sin archivos `.pkl`?**  
`tests/conftest.py` mocka loaders antes de import → 0 deps en CI.

**¿Rate limit?**  
30 req/60s per IP, solo `/predict` + `/analyze-content`. Bucketing por IP, eviction FIFO en 10K limit.

**¿SSRF protections?**  
`HtmlFetcher`: IPv4/RFC1918/link-local bloqueados, 5 hops max, 2MB cap.

---

**Actualizado**: 2026-08-25  
**Status**: Producción  
**Tests**: 535/535 passing
