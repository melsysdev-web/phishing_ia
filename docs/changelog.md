# Changelog

## 2026-08-21

### Publicación en la tienda: el paquete que iba a subirse estaba roto
- `scripts/package_extension.ps1` — empaquetado con validaciones. El ZIP 1.0.4 se armó a mano y salió roto de cuatro formas: `manifest.json` bajo `extension/` en vez de en la raíz (la tienda lo rechaza), sin `config.js` (el service worker hace `importScripts` de él, así que la extensión no arrancaba), con la URL apuntando a `http://localhost:8000` y sin el host del backend en `host_permissions`. Ninguno se ve en el código fuente, solo en el paquete: el script valida el ZIP ya construido y lo borra si el manifest no quedó en la raíz
- `docs/EDGE_ADDON_UPLOAD.md` documentaba justamente la estructura que provoca el rechazo, en dos sitios. Corregido, y el árbol regenerado del contenido real
- Versión del manifest a `1.0.0`: es una ficha nueva, y `1.0.4` quedó quemado en un ZIP cuyo contenido no se corresponde con ese número

### anime.js retirado (bloqueaba la publicación)
- `popup.html` y `sidebar.html` cargaban anime.js desde `cdn.jsdelivr.net`. Manifest V3 prohíbe el código remoto y las tiendas rechazan automáticamente por ello
- No hacía nada: la CSP de MV3 ya bloqueaba el script, de modo que lo que corría era el polyfill de respaldo. No se perdió ninguna animación que estuviera funcionando
- La extensión es ahora autocontenida: no pide ningún host salvo su propio backend. El empaquetador rechaza cualquier `<script src="https://...">`

### Backend público, pero declarado
- `ALLOW_UNAUTHENTICATED` — `ENVIRONMENT=production` sin `API_KEY` sigue abortando el arranque, salvo que la decisión se declare. Entonces arranca y avisa por WARNING en cada arranque
- El motivo: la extensión se publica en una tienda y su paquete es descomprimible, así que una clave embebida sería pública desde el primer día
- `BACKEND_IS_PUBLIC` en `extension/config.js` refleja la misma decisión en el cliente; el empaquetador se niega a construir un paquete donde ambos se contradigan
- 18 tests nuevos (`backend/tests/test_auth_config_guard.py`)

### Documentación
- Conteos de tests corregidos en cinco archivos que daban cifras distintas (281, 324, 446, 517) — son **535**
- `docs/EDGE_STORE_DESCRIPTIONS.md` reescrito: listaba "Google Chrome (v120+)", que Edge prohíbe mencionar, y anunciaba animaciones inexistentes. Ahora contiene los textos definitivos de la ficha, la justificación de los siete permisos y la lista de comprobación previa al envío
- `docs/EXTENSION_STABILITY.md`: la sección del CDN describía una defensa que ya no aplica
- `DEPLOYMENT.md`, `api.md`, `README.md`, `CLAUDE.md`, `CLAUDE_ES.md` sincronizados con el modelo de autenticación público

---

## 2026-08-19 — 2026-08-21 (rama `fix/logging-and-deploy-smoke-test`)

- **El logging del backend no emitía nada**: configurado de verdad, con `LOG_LEVEL` y respaldo a `INFO` ante un valor irreconocible
- **Smoke test que llama a `/predict`**, no a `/health`: ambos devolvían 200 mientras `/predict` daba 502, porque `/metadata` solo hace `.exists()` sobre los archivos de modelo y el pipeline degrada con elegancia
- **Cuantización int8 eliminada**: era la causa del 502 en Render. Materializaba todos los pesos al convertirlos (+735 MB de pico) para ganar 1,96 ms/URL en un pipeline de 3-8 s dominado por E/S de red. `/predict` bajó de 1213 MB a 791 MB
- **Semáforo de concurrencia** (`MAX_CONCURRENT_ANALYSES`): dos análisis simultáneos en 512 MB provocaban un OOM que se llevaba el worker entero
- **Scoring calibrado**, penalización de guiones corregida (`num_hyphens_domain` en vez de `num_hyphens`) y bucle de feedback con URLs hasheadas en SHA-256
- La extensión apuntaba a un host de Render inexistente; URL y clave centralizadas en `extension/config.js` para que popup, sidebar, opciones y service worker no puedan desincronizarse

---

## 2026-08-06 — 2026-08-19

- **Seguridad**: probabilidades invertidas del Random Forest corregidas (sesgaban en silencio el 40% de la fusión), guardián de SSRF en el fetcher de HTML con cierre del hueco de DNS-rebinding, etiqueta invertida en `FusionEngine`, CVEs de Debian purgados de la imagen Docker, página de opciones oculta a los usuarios finales
- **Cuota de VirusTotal**: envío innecesario eliminado, circuit breaker global de cuota y capa de cache templada de 30 días
- **Modelos horneados en la imagen Docker** desde Hugging Face Hub (`MODELS_DIR=/models`)
- **Monitorización local** con Prometheus y Grafana; trazado distribuido con OpenTelemetry
- **Auditoría de tests** y reestructuración modular de la documentación
- Permisos de la extensión ajustados para Edge Add-ons

---

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
