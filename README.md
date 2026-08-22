# AI Phishing Detector

Extensión para navegadores basados en Chromium (Edge, Chrome) que detecta sitios de phishing en tiempo real mediante un pipeline multicapa: análisis de URL, WHOIS, HTML, tres modelos de Machine Learning y tres APIs de inteligencia de amenazas.

---

## Características

- **Score visual 0–100** con veredicto LOW / MEDIUM / HIGH
- **Confianza calibrada**: cada veredicto reporta cuánto confiar en él, y baja cuando los modelos discrepan o hay pocas señales
- **9 señales independientes**: si una API falla, las demás siguen operando
- **Pipeline paralelo**: 6 tareas I/O en paralelo → resultado en 3–8 s
- **Cache de dos capas**: 10 min en memoria + 30 días en SQLite para no gastar cuota de API en URLs repetidas
- **Explicable**: cada veredicto incluye las razones en lenguaje natural
- **Corregible**: el usuario puede reportar un veredicto equivocado desde el sidebar
- **Extensión completa**: popup minimalista, sidebar con análisis completo, página de opciones

---

## Arquitectura

```
Chrome Extension (popup / sidebar / options)
        │  POST /predict
        ▼
FastAPI Backend
        │
        ├── URL Feature Extraction (12 features, instantáneo)
        │
        ├── Grupo 1 — paralelo (6 workers):
        │   ├── WHOIS / Domain Info
        │   ├── HTML Fetch + Parse
        │   ├── VirusTotal API
        │   ├── Google Safe Browsing API
        │   ├── Google Fact Check API
        │   └── RoBERTa URL Classifier
        │
        ├── Grupo 2 — depende del HTML:
        │   └── Random Forest (34 features URL+HTML)
        │
        └── FusionEngine (RF×0.4 + RoBERTa×0.6)
                └── RiskEngine → score 0-100 + reasons
```

Ver [`docs/architecture.md`](docs/architecture.md) para detalles completos.

---

## Requisitos

- Python 3.12+
- Un navegador basado en Chromium para la extensión (Edge o Chrome)
- GPU NVIDIA con CUDA (recomendado para entrenamiento; no necesario para inferencia)
- Claves de API (opcionales — el sistema funciona sin ellas con capacidad reducida):
  - `VIRUSTOTAL_API_KEY`
  - `SAFE_BROWSING_API_KEY`
  - `FACT_CHECK_API_KEY`

---

## Instalación

```powershell
# 1. Clonar y crear entorno virtual
git clone <repo-url>
cd phishing_ia
python -m venv venv

# 2. Instalar dependencias
venv\Scripts\pip install -r requirements.txt
```

`requirements.txt` fija `torch`/`torchvision`/`torchaudio` con el sufijo `+cu128` (build CUDA 12.8). Si la máquina no tiene una GPU NVIDIA compatible con CUDA 12.8, ese paso falla al no encontrar la wheel. En ese caso, instalar antes la variante CPU (o la que corresponda a la GPU disponible) y luego el resto:

```powershell
venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
venv\Scripts\pip install -r requirements.txt
```

```powershell
# 3. Configurar claves de API
# Crear .env en la raíz del proyecto (no está versionado) con el siguiente contenido
```

### `.env`
```env
VIRUSTOTAL_API_KEY=tu_clave_aqui
SAFE_BROWSING_API_KEY=tu_clave_aqui
FACT_CHECK_API_KEY=tu_clave_aqui

# Clave de autenticación del backend (dejar vacío = sin autenticación)
API_KEY=

# Orígenes CORS adicionales separados por coma (ej: https://mi-app.com)
ALLOWED_ORIGINS=

# production | development (default). En production el backend no arranca sin
# API_KEY, salvo que se declare ALLOW_UNAUTHENTICATED, y oculta el campo
# `detail` de los errores para no filtrar internals
ENVIRONMENT=development

# Declara que la exposición pública es intencionada (ver "Despliegue")
ALLOW_UNAUTHENTICATED=
```

### Modelos entrenados

La carpeta `models/` tampoco está versionada (pesa ~820 MB: `random_forest_v2.pkl` 25 MB + `roberta_phishing_new/` 317 MB + `roberta_content/` 479 MB). Los pesos viven en [Hugging Face](https://huggingface.co/mel3601/phishing-ia-models) y el `backend/Dockerfile` los descarga durante el build, así que el despliegue con Docker los trae solos. **En local no**: los cargadores (`joblib.load`, `from_pretrained` sobre una ruta) leen de disco y no descargan nada, de modo que hay que copiar la carpeta desde una instalación existente, bajarla del repo de Hugging Face, o reentrenar con los scripts de la sección [Modelos ML](#modelos-ml) — si el entrenamiento deja subcarpetas `checkpoint-*` dentro de `roberta_phishing_new/` o `roberta_content/`, se pueden borrar: son artefactos intermedios de HuggingFace `Trainer`, no se usan en inferencia y solo ocupan espacio. Sin `models/roberta_content/`, el Content Classifier cae automáticamente al fallback de HuggingFace (`hamzab/roberta-fake-news-classification`, se descarga solo); sin `random_forest_v2.pkl` o `roberta_phishing_new/`, esas señales fallan de forma controlada (el pipeline no se cae, ver `_safe()` en `phishing_service.py`).

---

## Ejecutar el Backend

```powershell
venv\Scripts\uvicorn backend.app.main:app --reload
```

El servidor queda disponible en `http://localhost:8000`.

**Endpoints:**
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/metadata` | Versión de la API, modelos ML disponibles y configuración activa |
| `POST` | `/predict` | Análisis completo de una URL |
| `POST` | `/analyze-content` | Clasificación de texto libre (REAL/FAKE) |
| `POST` | `/feedback` | Reportar un veredicto incorrecto (la URL se guarda hasheada) |
| `GET` | `/feedback/stats` | Correcciones acumuladas, con falsos positivos y negativos por separado |
| `GET` | `/experiment/status` | Configuración activa del experimento de scoring |
| `GET` | `/cache/stats` | Estadísticas del cache en memoria |
| `DELETE` | `/cache` | Limpiar cache |
| `GET` | `/` | Comprobación básica |
| `GET` | `/metrics` | Métricas Prometheus (fuera del esquema OpenAPI) |

Solo `/`, `/health`, `/metadata` y `/metrics` son públicos; el resto va detrás de `require_api_key`, que es un no-op cuando `API_KEY` está vacía.

Contrato completo, ejemplos de curl y códigos de error: [`docs/api.md`](docs/api.md).

---

## Probar la API sin escribir código

Con el backend corriendo, abrir **`http://localhost:8000/docs`** (Swagger UI, generado automáticamente por FastAPI): cada endpoint tiene un botón **Try it out** para ejecutar requests reales desde el navegador, sin curl ni Postman.

Para Postman: **Import → Link** → `http://localhost:8000/openapi.json` importa los endpoints con sus schemas.

Ejemplo con curl:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <tu_api_key>" \
  -d '{"url": "https://ejemplo.com"}'
```

Si `API_KEY` está vacío en `.env` (default en local), el header `X-API-Key` no es necesario.

---

## Despliegue en producción

El backend se puede correr con Docker (`docker compose up backend`, ver `docker-compose.yml` y `backend/Dockerfile`), pero Uvicorn expone HTTP plano sin TLS. Para cualquier despliegue accesible fuera de `localhost`:

- Poner un proxy inverso con TLS delante (nginx, Caddy, Traefik, etc.) — el contenedor del backend no debe exponerse directamente a internet.
- Configurar `ENVIRONMENT=production` y `API_KEY` en `.env`. Con `ENVIRONMENT=production`, el backend **rehúsa arrancar** si `API_KEY` está vacío (evita quedar sin autenticación por descuido).
- Si la exposición pública es intencionada, declararla con `ALLOW_UNAUTHENTICATED=true`: el backend arranca sin clave y lo avisa por WARNING en cada arranque. Es como corre el despliegue público de este proyecto, porque la extensión se distribuye en una tienda y su paquete no puede guardar un secreto. Quitar `ENVIRONMENT=production` para esquivar la comprobación es peor: también reactiva el campo `detail` en las respuestas de error.
- Revisar `ALLOWED_ORIGINS` si la extensión/cliente no corre desde `chrome-extension://` o `localhost`.

### Memoria requerida

Los pesos se descargan desde [Hugging Face](https://huggingface.co/mel3601/phishing-ia-models) durante el build de Docker y quedan horneados en la imagen (`MODELS_DIR=/models`), así que la distribución está resuelta. Lo que importa en runtime es la RAM.

Coste medido por etapa al atender `/predict`:

| Etapa | Δ RAM |
|---|---|
| `import torch` | +470 MB (build CUDA local; la rueda CPU de Docker es menor) |
| `transformers` + `fastapi` | +33 MB |
| Random Forest | +156 MB |
| RoBERTa URL | +115 MB |

`roberta_content` **no se carga** en `/predict`; sólo lo usa `/analyze-content`.

> Hasta el 2026-08-20 el cargador de RoBERTa cuantizaba a int8 para acelerar CPU. Medido, hacía lo contrario: materializaba todos los pesos y disparaba un pico de +735 MB que mataba al worker en el plan gratuito de Render (512 MB), devolviendo **502** en `/predict` y tumbando el servicio. Ganaba 1.96 ms por URL en un pipeline de 3–8 s. Se quitó.

`/metadata` informando `"models": true` **no prueba que funcionen**: sólo comprueba que los archivos existan en disco. Para verificar un despliegue hay que llamar a `/predict`.

---

## Instalar la Extensión

1. Abrir el navegador → `edge://extensions/` (o `chrome://extensions/`)
2. Activar **Modo desarrollador**
3. Clic en **Cargar descomprimida**
4. Seleccionar la carpeta `extension/`

La extensión abre el **popup** al hacer clic en el icono. El **sidebar** se abre desde el botón de paneles laterales del navegador. La URL del backend y la clave se definen en `extension/config.js` (`BACKEND_DEFAULT_URL`, que apunta al backend desplegado) y se pueden cambiar en **⚙️ Configuración** — útil para apuntar a `http://localhost:8000` mientras se desarrolla.

### Empaquetar para la tienda

```powershell
.\scripts\package_extension.ps1
```

Nunca comprimir `extension/` a mano: el `manifest.json` debe quedar en la **raíz** del ZIP, o la tienda lo rechaza con *"Manifest file is missing or unreadable"*. El script valida las referencias del manifest, que `config.js` esté incluido, que la URL del backend no sea `localhost` y esté declarada en `host_permissions`, que el modelo de autenticación sea coherente y que ningún HTML cargue código remoto (Manifest V3 lo prohíbe). Después vuelve a verificar el ZIP ya construido y lo borra si algo falla.

Para probar el paquete de verdad hay que descomprimirlo en una carpeta limpia y cargar **esa** carpeta: cargar `extension/` directamente oculta justamente los fallos de empaquetado.

---

## Modelos ML

Los modelos entrenados van en la carpeta `models/`:

| Archivo | Descripción |
|---|---|
| `random_forest_v2.pkl` | Random Forest — 34 features URL+HTML |
| `feature_columns_v2.pkl` | Orden de columnas del RF |
| `roberta_phishing_new/` | RoBERTa fine-tuned en URLs |
| `roberta_content/` | RoBERTa fine-tuned en noticias falsas/reales |

### Entrenar modelos

**Random Forest** (requiere `datasets/raw/phishing_urls.csv`):
```powershell
venv\Scripts\python training/train_random_forest.py
```

**RoBERTa URL** (requiere `datasets/roberta_dataset.csv`):
```powershell
venv\Scripts\python backend/app/roberta/trainer.py
```

**Content Classifier en inglés** (descarga `GonzaloA/fake_news` de HuggingFace):
```powershell
venv\Scripts\python backend/app/roberta/content_trainer.py
```

**Content Classifier en español**:
```powershell
venv\Scripts\python backend/app/roberta/content_trainer_es.py
```

> Si `models/roberta_content/` no existe, el Content Classifier usa automáticamente `hamzab/roberta-fake-news-classification` desde HuggingFace como fallback.

---

## Pruebas

```powershell
# Suite completa — 535 tests, sin necesidad de modelos ni claves de API
venv\Scripts\python -m pytest

# Un solo archivo
venv\Scripts\python -m pytest backend/tests/test_risk_engine.py -v

# Linter
venv\Scripts\python -m ruff check .

# Smoke test del Random Forest
venv\Scripts\python -m backend.app.random_forest.test_predict

# Verificar un despliegue (llama a /predict; /health no sirve como prueba)
venv\Scripts\python scripts\smoke_test.py --base-url https://<servicio>.onrender.com
```

`tests/conftest.py` sustituye los cargadores de modelos antes de que se importe nada del backend, así que la suite corre sin archivos `.pkl` ni modelos de HuggingFace presentes.

---

## Documentación

### Base del proyecto

| Documento | Descripción |
|---|---|
| [`docs/mvp_scope.md`](docs/mvp_scope.md) | Alcance, objetivos y qué queda dentro y fuera |
| [`docs/user_stories.md`](docs/user_stories.md) | Historias de usuario con criterios de aceptación |
| [`docs/decision_tree.md`](docs/decision_tree.md) | Lógica de puntuación del RiskEngine: cada delta, atenuaciones y salida calibrada |
| [`docs/testing_report.md`](docs/testing_report.md) | Casos de prueba manuales y cobertura de la suite automatizada |
| [`docs/presentacion.md`](docs/presentacion.md) | Presentación del proyecto con FAQ |

### Referencia técnica

| Documento | Descripción |
|---|---|
| [`docs/api.md`](docs/api.md) | Contrato de la API: endpoints, request/response, ejemplos curl, códigos de error |
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura completa, pipeline, módulos |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Despliegue en Render paso a paso, variables de entorno, troubleshooting |
| [`docs/TESTING.md`](docs/TESTING.md) | Estrategia de pruebas y cobertura |
| [`docs/EXTENSION_STABILITY.md`](docs/EXTENSION_STABILITY.md) | Código defensivo de la extensión y los fallos que absorbe |
| [`SCORE_IMPROVEMENTS_STRATEGY.md`](SCORE_IMPROVEMENTS_STRATEGY.md) | Qué entregó el trabajo de scoring y qué sigue bloqueado por falta de datos |
| [`docs/EDGE_ADDON_UPLOAD.md`](docs/EDGE_ADDON_UPLOAD.md) | Publicación en Microsoft Edge Add-ons, paso a paso |
| [`docs/EDGE_STORE_DESCRIPTIONS.md`](docs/EDGE_STORE_DESCRIPTIONS.md) | Textos de la ficha: descripciones, propósito único, justificación de cada permiso y comprobaciones previas al envío |
| [`PRIVACY_POLICY.md`](PRIVACY_POLICY.md) | Qué datos salen del navegador y qué no |
| [`docs/changelog.md`](docs/changelog.md) | Historial de cambios |

---

## Estructura del Proyecto

```
phishing_ia/
├── backend/app/
│   ├── core/config.py              # Config centralizada (env vars)
│   ├── api/routes.py               # Endpoints FastAPI
│   ├── services/                   # Pipeline: phishing, risk, VT, SB, FC, content
│   ├── ml/fusion/fusion_engine.py  # RF×0.4 + RoBERTa×0.6
│   ├── random_forest/              # Predictor + model loader
│   ├── roberta/                    # Predictor URL + trainers
│   ├── analyzers/                  # HTML fetch + feature extraction
│   └── utils/                      # URL features, WHOIS, feature mapper, cache
├── extension/
│   ├── config.js                   # URL y clave del backend — definición única
│   ├── popup/                      # UI mínima con gauge SVG
│   ├── sidebar/                    # Análisis completo
│   ├── options/                    # Configuración del backend
│   ├── background/                 # Service worker + health check periódico
│   ├── services/api_client.js      # Cliente HTTP de la extensión
│   ├── utils/error_messages.js     # Mensajes de error legibles
│   └── manifest.json
├── models/                         # Modelos entrenados (.pkl, directorios HF)
├── datasets/                       # Datasets de entrenamiento
├── training/                       # Scripts de entrenamiento RF
├── scripts/                        # Empaquetado, smoke test, memoria, entrenamiento
└── docs/                           # Documentación
```
