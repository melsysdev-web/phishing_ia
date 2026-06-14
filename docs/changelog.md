# Changelog

## 2026-06-13

### Limpieza de arquitectura
- Eliminados 6 archivos Python vacíos (`fusion/fusion_engine.py`, `services/roberta_service.py`, `ml/roberta_service.py`, `ml/explainability.py`, `ml/inference.py`, `ml/model_loader.py`)
- Eliminado `models/random_forest.pk1` (0 bytes, extensión con typo)
- Implementado `backend/app/core/config.py` con configuración centralizada y una sola llamada a `load_dotenv()`
- Refactorizados `virustotal_service.py`, `safe_browsing_service.py`, `fact_check_service.py` para importar desde `core/config`

### Extensión Chrome — Interfaz completa
- **Popup**: reescrito como UI mínima con input URL manual, botón pegar (aparece al enfocar el input), gauge SVG animado (0-100) con transición CSS y animación de número ease-out cubic
- **Sidebar**: panel lateral con análisis completo — veredicto, barra de score, sección ML (RF/RoBERTa/Fusion), Threat Intel (VT/SB/FC), razones completas, tab de clasificación de contenido
- **Options**: página de configuración de URL del backend con prueba de conexión y persistencia en `chrome.storage.sync`
- `api_client.js` lee `backendUrl` desde `chrome.storage.sync` en lugar de URL hardcodeada
- Eliminados permisos `tabs` y `activeTab` (ya no se auto-analiza la pestaña activa)
- `openPanelOnActionClick: false` — el popup es la UI principal, el sidebar se abre desde Chrome

### Documentación
- Creado `CLAUDE.md` con comandos, arquitectura y convenciones
- Actualizados todos los documentos en `docs/`

---

## 2026-06-10

### Pipeline paralelo + cache
- Reestructurado pipeline en 2 oleadas paralelas con `ThreadPoolExecutor`
- Implementado cache TTL en memoria (`url_cache.py`): 600s, 500 entradas
- Añadidos endpoints `GET /cache/stats` y `DELETE /cache`
- `_safe(fn, *args)` wraps todas las llamadas paralelas — errores no crashean el pipeline

### FusionEngine
- Implementado `ml/fusion/fusion_engine.py`: RF × 0.4 + RoBERTa URL × 0.6
- Degradación graceful: si un modelo falla, el otro opera al 100%

### Fact Check API
- Implementado `fact_check_service.py` con Google Fact Check Tools API v1alpha1
- Lógica de clasificación: reliable / suspicious / unreliable / no_data
- Distingue entre dominio como fuente vs. dominio como verificador

### RoBERTa Content Classifier
- `content_classifier_service.py` con lazy load vía `@lru_cache`
- Fallback a `hamzab/roberta-fake-news-classification` si no existe modelo local
- Normalización de labels: TRUE/FALSE (remoto) → REAL/FAKE (local)

---

## 2026-06-07

### RoBERTa URL Classifier
- Fine-tuning de `distilroberta-base` en URLs phishing/legítimas
- Guardado en `models/roberta_phishing/`
- Integrado en el pipeline principal como señal independiente

### HTML Analyzer
- `html_fetcher.py`: descarga HTML con timeout y manejo de errores
- `html_features.py`: extrae 6 features de página (título, favicon, formularios, JS, etc.)

---

## 2026-06-03

### MVP inicial
- FastAPI con CORS
- `url_features.py`: extracción de 12 features de URL
- `domain_utils.py`: wrapper WHOIS
- `risk_engine.py`: scorer aditivo 0-100
- `random_forest/`: Random Forest v2 con 14 features
- Chrome Extension Manifest V3 (estructura base)
- VirusTotal v3 integrado
- Google Safe Browsing v4 integrado
