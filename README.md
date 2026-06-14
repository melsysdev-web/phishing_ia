# AI Phishing Detector

Extensión para Google Chrome que detecta sitios de phishing en tiempo real mediante un pipeline multicapa: análisis de URL, WHOIS, HTML, tres modelos de Machine Learning y tres APIs de inteligencia de amenazas.

---

## Características

- **Score visual 0–100** con veredicto LOW / MEDIUM / HIGH
- **9 señales independientes**: si una API falla, las demás siguen operando
- **Pipeline paralelo**: 6 tareas I/O en paralelo → resultado en 3–8 s
- **Cache TTL 10 min** — URLs repetidas responden en < 5 ms
- **Explicable**: cada veredicto incluye las razones en lenguaje natural
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
        ├── Grupo 2 — paralelo (2 workers):
        │   ├── Random Forest (14 features URL+HTML)
        │   └── Content Classifier (RoBERTa fake-news)
        │
        └── FusionEngine (RF×0.4 + RoBERTa×0.6)
                └── RiskEngine → score 0-100 + reasons
```

Ver [`docs/architecture.md`](docs/architecture.md) para detalles completos.

---

## Requisitos

- Python 3.12+
- Google Chrome (para la extensión)
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

# 3. Configurar claves de API
copy .env.example .env
# Editar .env con tus claves
```

### `.env`
```env
VIRUSTOTAL_API_KEY=tu_clave_aqui
SAFE_BROWSING_API_KEY=tu_clave_aqui
FACT_CHECK_API_KEY=tu_clave_aqui
```

---

## Ejecutar el Backend

```powershell
venv\Scripts\uvicorn backend.app.main:app --reload
```

El servidor queda disponible en `http://localhost:8000`.

**Endpoints:**
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/predict` | Análisis completo de una URL |
| `POST` | `/analyze-content` | Clasificación de texto libre (REAL/FAKE) |
| `GET` | `/cache/stats` | Estadísticas del cache en memoria |
| `DELETE` | `/cache` | Limpiar cache |

---

## Instalar la Extensión

1. Abrir Chrome → `chrome://extensions/`
2. Activar **Modo desarrollador** (esquina superior derecha)
3. Clic en **Cargar descomprimida**
4. Seleccionar la carpeta `extension/`

La extensión abre el **popup** al hacer clic en el icono. El **sidebar** se abre desde el botón de paneles laterales de Chrome. La URL del backend se configura en **⚙️ Configuración** (default: `http://localhost:8000`).

---

## Modelos ML

Los modelos entrenados van en la carpeta `models/`:

| Archivo | Descripción |
|---|---|
| `random_forest_v2.pkl` | Random Forest — 14 features URL+HTML |
| `feature_columns_v2.pkl` | Orden de columnas del RF |
| `roberta_phishing/` | RoBERTa fine-tuned en URLs |
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
# Test completo del HTML analyzer
venv\Scripts\python -m pytest backend/app/analyzers/test_html_analyzer.py -v

# Smoke test del Random Forest
venv\Scripts\python -m backend.app.random_forest.test_predict
```

---

## Documentación

| Documento | Descripción |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura completa, pipeline, módulos |
| [`docs/decision_tree.md`](docs/decision_tree.md) | Lógica de puntuación del RiskEngine |
| [`docs/mvp_scope.md`](docs/mvp_scope.md) | Alcance e implementación del proyecto |
| [`docs/testing_report.md`](docs/testing_report.md) | Casos de prueba y resultados |
| [`docs/user_stories.md`](docs/user_stories.md) | Historias de usuario |
| [`docs/changelog.md`](docs/changelog.md) | Historial de cambios |
| [`docs/presentacion.md`](docs/presentacion.md) | Presentación del proyecto con FAQ |

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
│   ├── popup/                      # UI mínima con gauge SVG
│   ├── sidebar/                    # Análisis completo
│   ├── options/                    # Configuración del backend
│   ├── services/api_client.js      # Cliente HTTP de la extensión
│   └── manifest.json
├── models/                         # Modelos entrenados (.pkl, directorios HF)
├── datasets/                       # Datasets de entrenamiento
├── training/                       # Scripts de entrenamiento RF
└── docs/                           # Documentación
```
