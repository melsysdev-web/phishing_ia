# CLAUDE.md

Este archivo proporciona orientación a Claude Code (claude.ai/code) al trabajar con código en este repositorio.

## Descripción General

Detector de Phishing con IA: un backend FastAPI + extensión Chrome (Manifest V3) que analiza URLs en busca de riesgo de phishing usando un pipeline multi-señal de ML (características de URL/HTML, WHOIS, tres APIs de inteligencia de amenazas y tres modelos de ML).

## Comandos

Todos los comandos se ejecutan desde la raíz del repositorio. El venv está en `venv/`.

**Ejecutar el backend:**
```powershell
venv\Scripts\uvicorn backend.app.main:app --reload
```
Se sirve en `http://localhost:8000`.

**Ejecutar la suite completa de pruebas** (`[tool.pytest.ini_options]` en `pyproject.toml` establece `testpaths = ["tests", "backend/tests"]`):
```powershell
venv\Scripts\python -m pytest
```

**Linter** (`[tool.ruff]`/`[tool.ruff.lint]` en `pyproject.toml`: longitud de línea 100, py312, reglas `E,F,I,B`; `scripts/generate_*.py` están exentos de `E501` ya que sus líneas largas son contenido de reportes/diagramas narrativos, no lógica):
```powershell
venv\Scripts\python -m ruff check .
```

**Ejecutar un archivo de prueba individual:**
```powershell
venv\Scripts\python -m pytest backend/tests/test_risk_engine.py -v
```

`tests/conftest.py` parchea `backend.app.random_forest.model_loader` y `backend.app.roberta.model_loader` en `sys.modules` **antes** de que se importe cualquier código del backend, por lo que la suite completa de pruebas se ejecuta sin archivos `.pkl`/modelo HF reales presentes. Las pruebas que importan `backend.app.main` (p.ej. `tests/test_content_api.py`) obtienen esto de forma gratuita siempre que conftest se cargue primero (comportamiento predeterminado de pytest). También define una fixture `autouse` que limpia el `_rate_store` de `RateLimitMiddleware` antes de cada prueba — el limitador agrupa por IP únicamente (no por ruta), por lo que sin el reinicio, las pruebas que golpean `/predict`/`/analyze-content` en secuencia dispararían 429s de pruebas anteriores.

**Prueba rápida de modelo de humo (Random Forest):**
```powershell
venv\Scripts\python -m backend.app.random_forest.test_predict
```

**Entrenar Random Forest** (requiere `datasets/raw/phishing_urls.csv`, guarda `random_forest_v2.pkl` + `feature_columns_v2.pkl` en `models/`):
```powershell
venv\Scripts\python training/train_random_forest.py
```

**Entrenar clasificador RoBERTa URL** (requiere `datasets/roberta_dataset.csv`, guarda en `models/roberta_phishing_new`):
```powershell
venv\Scripts\python backend/app/roberta/trainer.py
```

**Entrenar clasificador de contenido (noticias falsas / REAL-FAKE)** (descarga `GonzaloA/fake_news` de HuggingFace, guarda en `models/roberta_content`):
```powershell
venv\Scripts\python backend/app/roberta/content_trainer.py
```

**Entrenador de contenido en español** (mismo propósito, dataset en español):
```powershell
venv\Scripts\python backend/app/roberta/content_trainer_es.py
```

**Entrenar clasificador de phishing independiente** (RoBERTa personalizado + cabeza de clasificador, requiere un CSV con columnas `url,body,label`; guarda en `checkpoints/phishing_detector/best_model.pt`):
```powershell
venv\Scripts\python scripts\run_training.py datasets\mi_dataset.csv
```

`models/` no está versionado (`.gitignore`); `datasets/raw/phishing_urls.csv` está versionado. Sin `random_forest_v2.pkl` o `roberta_phishing_new/`, esas señales fallan de manera controlada (`_safe()` en `phishing_service.py` retorna `{"error": ...}` en lugar de romper el pipeline). Sin `models/roberta_content/`, `ContentClassifierService` retrocede al modelo del hub de HuggingFace `hamzab/roberta-fake-news-classification`.

## Arquitectura

### Pipeline de análisis (`POST /predict`)

`PhishingService.analyze` se ejecuta en dos olas paralelas, luego secuencialmente:

1. **Grupo 1 (paralelo, 6 trabajadores):** la extracción de características de URL es solo CPU y se ejecuta antes de la ola. Luego en paralelo: información de dominio WHOIS, obtención+análisis de HTML, API de VirusTotal, API de Google Safe Browsing, API de Fact Check, clasificador RoBERTa URL.

2. **Grupo 2:** depende del resultado HTML — Random Forest (características mapeadas).

3. **Secuencial:** FusionEngine combina puntuaciones de RF + RoBERTa URL (ponderadas 40/60), luego `RiskEngine.calculate` agrega todas las señales en una puntuación de 0–100 con razones legibles por humanos, retornando riesgo `LOW/MEDIUM/HIGH`. `content_classification` es siempre `None` en la respuesta `/predict` — la clasificación de contenido solo ocurre a través del endpoint `/analyze-content` separado, no forma parte del pipeline de fusión de URL.

Los resultados se cachean en memoria (TTL 10 min, máx 500 entradas) indexados por URL.

### Seguridad de API (`backend/app/core/`)

- `config.py` carga `.env` en un singleton `settings`: `virustotal_api_key`, `safe_browsing_api_key`, `fact_check_api_key`, `api_key` (autenticación del backend, vacío = deshabilitado), `allowed_origins` (orígenes CORS adicionales separados por comas).
- `security.py` — `require_api_key` es una dependencia de FastAPI aplicada a todo el router en `routes.py` (`APIRouter(dependencies=[Depends(require_api_key)])`). Lee el encabezado `X-API-Key`; si `settings.api_key` está vacío, la verificación es una no-op (autenticación deshabilitada), de lo contrario, el encabezado debe coincidir exactamente o retorna 403.
- `settings.environment` (`ENVIRONMENT` variable de entorno, predeterminado `development`) — si se establece en `production` sin `API_KEY` configurada, `main.py` lanza `RuntimeError` al iniciarse en lugar de arrancar un backend sin autenticación.
- `main.py` también registra un `RateLimitMiddleware` personalizado: 30 solicitudes/60s por IP de cliente, limitado a `/predict` y `/analyze-content` solamente, retorna 429 con `Retry-After: 60` cuando se excede (indexado por IP únicamente, no por ruta — los dos endpoints comparten un bucket). El `_rate_store` en memoria está limitado a 10,000 IPs distintas (`_RATE_MAX_IPS`), evictando la entrada más antigua una vez lleno, por lo que no puede crecer sin límite a partir de IPs puntuales/falsificadas. También registra `RequestLoggingMiddleware`, que registra método/ruta/estado/latencia/IP para cada solicitud.
- `require_api_key` compara el encabezado `X-API-Key` con `hmac.compare_digest`, no `==`, para evitar un ataque de tiempo en la comparación de claves.
- CORS (`main.py`) usa `allow_origin_regex` (no una lista estática) para aceptar cualquier origen `chrome-extension://` más `localhost`/`127.0.0.1`, extendido con `settings.allowed_origins` si se establece.
- Un `@app.exception_handler(Exception)` global en `main.py` atrapa errores no manejados, registra el traceback, y retorna un 500 con `{"error": ..., "detail": ...}` — `detail` se omite cuando `settings.environment == "production"` para evitar filtrar internals.

### Modelos de ML

| Archivo | Usado por | Versionado |
|---|---|---|
| `random_forest_v2.pkl` | `RandomForestPredictor` — predice phishing a partir de 34 características de URL/HTML | HuggingFace Hub |
| `feature_columns_v2.pkl` | orden de columnas para el modelo RF | HuggingFace Hub |
| `roberta_phishing_new/` | `RobertaPredictor` — `distilroberta-base` ajustado finamente en cadenas URL | HuggingFace Hub |
| `roberta_content/` | `ContentClassifierService` — clasificador de noticias FAKE/REAL (retrocede a `hamzab/roberta-fake-news-classification` si el directorio falta) | HuggingFace Hub |

Los tres cargadores resuelven este directorio a través de `get_models_dir()` en `backend/app/core/paths.py`, que predeterminadamente es `<raíz del repo>/models` y puede ser anulado con la variable de entorno `MODELS_DIR` (usada por el deployment de Docker, ver "Deployment" abajo). Los archivos de modelo están versionados en HuggingFace Hub y se descargan/cachean en el primer uso.

### APIs Externas (variables de entorno en `.env`)

- `VIRUSTOTAL_API_KEY` — VirusTotal v3
- `SAFE_BROWSING_API_KEY` — Google Safe Browsing v4
- `FACT_CHECK_API_KEY` — Google Fact Check Tools API
- `API_KEY` — clave de autenticación propia del backend, verificada contra el encabezado de solicitud `X-API-Key` (vacío desactiva autenticación)
- `ALLOWED_ORIGINS` — orígenes CORS adicionales más allá de la regex chrome-extension/localhost integrada
- `MODELS_DIR` — anula dónde los cargadores de modelos buscan `models/` (leído directamente via `os.getenv` en `backend/app/core/paths.py`, no a través del singleton `settings`); predeterminadamente `<raíz del repo>/models`, establecido en `/models` en el deployment de Docker

### Todos los endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/predict` | Pipeline completo de análisis de URL, retorna resultado cacheado si está disponible |
| `POST` | `/analyze-content` | Solo texto sin procesar → `ContentClassifierService` (REAL/FAKE); textos menores de 300 caracteres retornan un veredicto `no_content`/`UNKNOWN` en lugar de ser clasificados |
| `GET` | `/health` | Verificación de liveness usada por la prueba de conexión de la extensión |
| `GET` | `/` | Verificación de cordura de raíz |
| `GET` | `/metadata` | Versión de API, qué archivos de modelo ML están presentes en disco, y configuración activa de rate-limit/caché |
| `GET` | `/cache/stats` | Estadísticas de aciertos/fallos de caché y número de entradas |
| `DELETE` | `/cache` | Desalojar todos los resultados cacheados |
| `GET` | `/metrics` | Endpoint de recolección de Prometheus (métricas de solicitud/latencia + duración de inicio), no en el esquema OpenAPI — ver "Monitoring" abajo |

Todo el router (incluyendo `/predict`, `/analyze-content` y los endpoints de caché) está detrás de `require_api_key`; solo `/`, `/health`, `/metadata` y `/metrics` (todos definidos directamente en `app` en `main.py`) están sin autenticación. Cada endpoint tiene un `response_model` de Pydantic tipado de `backend/app/schemas/response_schema.py` para el contrato OpenAPI/Swagger, excepto `/metrics` (formato de exposición de Prometheus en texto plano, agregado por `prometheus-fastapi-instrumentator`, excluido del esquema via `include_in_schema=False`). Contrato completo de solicitud/respuesta con ejemplos curl: `docs/api.md`.

### Extensión Chrome (`extension/`)

Manifest V3. La URL del backend predeterminadamente es `http://localhost:8000` y es configurable a través de la página de opciones (almacenada en `chrome.storage.sync`). Si `API_KEY` está establecido en el backend, la página de opciones de la extensión también debe recibir esa clave para que `services/api_client.js` pueda enviarla como `X-API-Key`.

`background.js` solo establece `openPanelOnActionClick: false` en la instalación — **no** auto-analiza pestañas. El análisis es siempre iniciado por el usuario.

Dos UIs comparten `services/api_client.js`:
- **Popup** (`popup/`) — medidor compacto, análisis solo de URL
- **Sidebar** (`sidebar/`) — panel más enriquecido con dos pestañas: análisis de URL (veredicto, barras de modelo ML, inteligencia de amenazas) y análisis de contenido (llama a `POST /analyze-content` con texto pegado)

`content.js` es un placeholder reservado para inyección de banner en página futura.


### Disposición de módulos

```
backend/app/
  api/routes.py          # Router FastAPI (detrás de require_api_key), 2 endpoints de análisis + operaciones de caché
  main.py                # Entrada de app, CORS, RateLimitMiddleware, RequestLoggingMiddleware, manejador de excepción global, /, /health, /metadata
  core/
    config.py            # Carga .env en un singleton settings (claves de API, api_key del backend, allowed_origins)
    security.py          # Dependencia require_api_key (verificación de encabezado X-API-Key)
  services/
    phishing_service.py  # Orquesta el pipeline completo
    risk_engine.py        # Agregador de puntuación (basado en reglas, 0-100)
    content_classifier_service.py
    virustotal_service.py
    safe_browsing_service.py
    fact_check_service.py
  ml/fusion/fusion_engine.py  # Combinador ponderado RF+RoBERTa
  random_forest/         # Cargador, predictor y entrenador del modelo RF
  roberta/               # Modelo RoBERTa URL; entrenadores de contenido
  analyzers/             # Obtención de HTML (html_fetcher) + extracción de características (html_features, html_analyzer)
  utils/
    url_features.py      # Extracción de características de cadena URL
    domain_utils.py       # Envoltorio WHOIS
    feature_mapper.py     # Mapea características url+html → entrada de RF
    url_cache.py          # Caché en memoria thread-safe con TTL
  schemas/
    request_schema.py     # UrlRequest (valida prefijo http/https), TextRequest
    response_schema.py     # response_model para cada endpoint (contrato OpenAPI), incl. MetadataResponse, ErrorResponse
    ml_response.py         # Modelo Pydantic MLPredictionResponse

backend/tests/            # Pruebas unitarias (url_features, html_features, feature_mapper, risk_engine, html_analyzer, content_classifier)
tests/                    # Pruebas a nivel de raíz + conftest.py (mocks de cargador de modelos compartidos por ambos directorios de pruebas)

training/                  # Pipeline de entrenamiento de Random Forest (separado de backend/app/roberta/)
  train_random_forest.py   # requiere datasets/raw/phishing_urls.csv → models/random_forest_v2.pkl
  preprocess.py, create_roberta_dataset.py, check_roberta_dataset.py

scripts/
  run_training.py             # CLI: CSV(url,body,label) → entrena → evalúa (phishing_detector/)
  test_phishing_url.py         # verificación single-URL ad-hoc contra phishing_detector/
  augment_roberta_dataset.py    # aumentación de dataset para el entrenador de RoBERTa URL

docs/                      # api.md, architecture.md, decision_tree.md, mvp_scope.md, testing_report.md, user_stories.md, changelog.md, presentacion.md
```

## Convenciones clave

- `RiskEngine` inicia cada URL en una puntuación de **50** y aplica deltas positivos/negativos de cada señal. El rango final se fija a 0–100; ≥80 = riesgo LOW, ≥50 = MEDIUM, <50 = HIGH.
- `_safe(fn, *args)` en `phishing_service.py` envuelve cada llamada paralela; un sub-servicio fallido retorna `{"error": "..."}` y nunca rompe el pipeline.
- Los tres cargadores de modelos (`random_forest/model_loader.py`, `roberta/model_loader.py`, `ContentClassifierService`) son perezosos y descargan de HuggingFace Hub en la primera llamada — cargan via `@lru_cache`-wrapped `get_model()` en la primera llamada, no en el tiempo de importación. Los modelos descargados se cachean localmente en `./models`. Si internet no está disponible o HuggingFace es inalcanzable, esa señal falla via `_safe()` y no rompe la app.
- `FusionEngine` degrada elegantemente: si un modelo da error, usa el otro a peso completo.
- `ContentClassifierService` se carga perezosamente (via `@lru_cache`) en la primera llamada; usa el modelo de HuggingFace `hamzab/roberta-fake-news-classification` por defecto. Entradas menores de 300 caracteres cortocircuitan a un resultado `no_content`/`UNKNOWN`/`0.0` en lugar de ejecutarse a través del modelo.
- Normalización de etiqueta en `ContentClassifierService`: el modelo retorna `TRUE/FALSE`, normalizado a `REAL/FAKE`.
- El Random Forest espera exactamente las columnas en `feature_columns_v2.pkl`; `FeatureMapper.map` debe producir esas claves (las faltantes predeterminan a 0).
- `HtmlFetcher.get_html` (`backend/app/analyzers/html_fetcher.py`) tiene protecciones SSRF desde que la URL que obtiene es controlada por el usuario via `/predict`: solo esquemas `http`/`https`, cada nombre de host se resuelve y se rechaza si alguna de sus IPs es privada/loopback/link-local/reservada/multicast/sin especificar (bloquea localhost, RFC1918 y endpoints de metadatos en la nube como `169.254.169.254`), los redireccionamientos se siguen manualmente (máx 5 saltos) con la verificación de host reaplicada en cada salto, y el cuerpo de respuesta se limita a 2 MB. Cualquier cambio en cómo el backend obtiene URLs controladas por atacante debe preservar estas verificaciones.
- La convención de etiqueta del Random Forest es `0 = phishing, 1 = legítimo`; `RandomForestPredictor` debe mapear `predict_proba` en consecuencia (`phishing_probability` de la clase 0, `legitimate_probability` de la clase 1) — estos fueron previamente invertidos, sesgando silenciosamente el 40% de la puntuación de fusión, así que trata este mapeo como determinante al tocar `random_forest/predictor.py`.
- `get_domain_info` pasa `timeout=10` a `whois.whois()` para que un servidor WHOIS lento/no responsivo no pueda cuelgar la solicitud `/predict` completa.
- La extensión (`popup.js`, `sidebar.js`) construye nodos DOM de historial y lista de razones via APIs DOM seguras (`createElement`/`textContent`), no interpolando URLs o cadenas de razón de `RiskEngine` en `innerHTML` — ambas son influenciables por atacante (la URL analizada, y texto raspado de la página analizada).
- Al agregar nuevas pruebas de backend, colócalas en `backend/tests/` (no un directorio nuevo a nivel superior) para que `testpaths` de `pyproject.toml` y los mocks de cargador de modelos compartidos de `conftest.py` las recojan automáticamente.

## 📚 Documentación Completa

- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — Diagrama del pipeline, scoring de RiskEngine, modelos ML, extensión Chrome
- **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)** — Guía paso a paso Render, variables de entorno, troubleshooting
- **[`docs/TESTING.md`](docs/TESTING.md)** — Resultados del audit de tests, nueva cobertura, ejecutar tests localmente
- **[`docs/API.md`](docs/API.md)** — Referencia de endpoints con ejemplos curl
- **[`docs/changelog.md`](docs/changelog.md)** — Cambios recientes y versiones

---

## Despliegue (Render, Docker)

**→ Ver [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) para guía completa paso a paso.**

Resumen rápido:
- Establece **Dockerfile path** a `backend/Dockerfile` (Render no lo auto-detecta)
- Configura variables de entorno: `VIRUSTOTAL_API_KEY`, `SAFE_BROWSING_API_KEY`, `FACT_CHECK_API_KEY`, `API_KEY` (opt), `FORWARDED_ALLOW_IPS=*`, `ENVIRONMENT`
- Los modelos descargan de HuggingFace Hub durante el build (~60-90s cold start)
- Habilita Auto-Deploy en push a `main`
- Servicio en `https://<service-name>.onrender.com`
## Pruebas

✅ **281 tests pasando** — Tests unitarios + integración con 100% de mocking de modelos (sin archivos de modelo reales necesarios).

**→ Ver [`docs/TESTING.md`](docs/TESTING.md) para estrategia de testing y resultados del audit (49 nuevos tests agregados 2026-08-17).**

Tests clave:
- Guard SSRF (34): Validación de IP, prevención de DNS-rebinding
- Rate limiting (7): Headers de proxy, bucketing, eviction
- Seguridad (8): Filtrado de errores, no filtrar internals
- Pipeline completo (200+): Características URL, análisis HTML, fusión, scoring de riesgo

## Monitoring (Prometheus + Grafana, solo local)

Visibilidad local via `docker-compose.yml` (no desplegado en Render):
- `GET /metrics` expone métricas Prometheus: `http_requests_total`, histogramas de latencia, `app_startup_duration_seconds`
- `docker compose up -d backend prometheus grafana` inicia stack con dashboard auto-aprovisionado
- Grafana en `http://localhost:3000`, Prometheus en `http://localhost:9090`

## CI (`.github/workflows/ci.yml`)

Se ejecuta en push/PR a `main`: checkout → Python 3.12 → `pip install -r requirements-dev.txt --extra-index-url https://download.pytorch.org/whl/cpu` → `ruff check .` → `pytest -v`.

- `requirements-dev.txt` = `backend/requirements.txt` (torch CPU) + `pytest`/`ruff` fijados — deliberadamente *no* la `requirements.txt` raíz, que fija `torch==...+cu128` y fallaría para resolver en un ejecutor de GitHub Actions sin GPU.
- El flag `--extra-index-url` es requerido para que la rueda `+cpu` de torch se resuelva; sin él, `pip install` falla con "No matching distribution found".
- No se necesitan archivos de modelo o secretos `.env` para CI — `tests/conftest.py` simula los cargadores de RF/RoBERTa antes de la importación, así que la suite completa se ejecuta contra los mismos mocks usados localmente.
