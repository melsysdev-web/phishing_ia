# API Reference — AI Phishing Detector

Referencia de contrato para consumir el backend desde un cliente externo
(Swagger UI, curl, Postman, o cualquier cliente HTTP). Para arquitectura y
pipeline interno ver [`architecture.md`](architecture.md).

- **Base URL (local):** `http://localhost:8000`
- **Swagger UI interactivo:** `http://localhost:8000/docs`
- **OpenAPI spec (importable a Postman):** `http://localhost:8000/openapi.json`
- **Auth:** header `X-API-Key`, requerido solo si el backend tiene `API_KEY` configurada en `.env` (por defecto está vacío = sin autenticación en local)

## Endpoints

| Método | Ruta | Tag | Auth | Rate limit |
|---|---|---|---|---|
| `GET` | `/` | Sistema | No | No |
| `GET` | `/health` | Sistema | No | No |
| `GET` | `/metadata` | Sistema | No | No |
| `POST` | `/predict` | Análisis | Sí | 30 req/60s por IP |
| `POST` | `/analyze-content` | Análisis | Sí | 30 req/60s por IP |
| `GET` | `/cache/stats` | Cache | Sí | No |
| `DELETE` | `/cache` | Cache | Sí | No |

---

### `GET /health`

Liveness check. Sin autenticación.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "healthy" }
```

---

### `GET /metadata`

Versión de la API, modelos ML disponibles en el servidor y configuración activa (rate limit, cache). Útil para que un cliente externo verifique capacidades antes de llamar a `/predict` sin tener que leer el código.

```bash
curl http://localhost:8000/metadata
```

```json
{
  "api_version": "1.0.0",
  "models": {
    "random_forest": true,
    "roberta_url": true,
    "roberta_content": true
  },
  "rate_limit_per_minute": 30,
  "cache_ttl_seconds": 600,
  "cache_max_size": 500
}
```

`models.*` es `false` si el artefacto correspondiente no existe en `models/` (o en `MODELS_DIR` en despliegue) — la señal ML asociada falla en forma controlada en `/predict` en vez de tumbar el pipeline (ver `_safe()` en `phishing_service.py`).

---

### `POST /predict`

Pipeline completo de análisis de una URL: WHOIS, HTML, VirusTotal, Google Safe Browsing, Google Fact Check, Random Forest y RoBERTa, fusionados en un score 0–100. Resultado cacheado 10 minutos.

**Request**

```json
{ "url": "https://ejemplo.com" }
```

`url` debe empezar con `http://` o `https://`; si no, `422`.

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <tu_api_key>" \
  -d '{"url": "https://ejemplo.com"}'
```

**Response 200**

```json
{
  "url": "https://ejemplo.com",
  "cached": false,
  "analysis_time_ms": 1847,
  "risk_assessment": {
    "risk": "LOW",
    "confidence": 85,
    "score": 85,
    "reasons": ["HTTPS válido", "Dominio de marca verificada: ejemplo.com", "..."]
  },
  "machine_learning": {
    "fusion":        { "prediction": 0, "phishing_probability": 0.21, "legitimate_probability": 0.79, "rf_weight": 0.4, "roberta_weight": 0.6 },
    "random_forest": { "prediction": 0, "phishing_probability": 0.18, "legitimate_probability": 0.82 },
    "roberta":       { "prediction": 0, "phishing_probability": 0.24, "legitimate_probability": 0.76 }
  },
  "html_analysis":          { "success": true, "html_features": { "...": "..." } },
  "url_features":           { "has_https": true, "url_length": 23, "...": "..." },
  "domain_info":            { "domain": "ejemplo.com", "tld": "com", "domain_age_days": 4380 },
  "virustotal":             { "verdict": "clean" },
  "safe_browsing":          { "is_threat": false },
  "fact_check":             { "verdict": "reliable" },
  "content_classification": null
}
```

`content_classification` es siempre `null` en `/predict` — la clasificación de contenido solo corre vía `/analyze-content`.

Cada sub-señal (`html_analysis`, `virustotal`, `safe_browsing`, `fact_check`, cada modelo dentro de `machine_learning`) puede degradarse de forma independiente a `{"error": "..."}` si su servicio falla, sin afectar al resto del pipeline ni al status code de la respuesta.

---

### `POST /analyze-content`

Clasifica texto libre como `REAL` o `FAKE` (fake news / contenido engañoso).

**Request**

```json
{ "text": "..." }
```

Textos con menos de 300 caracteres no se clasifican (ver Response abajo).

```bash
curl -X POST http://localhost:8000/analyze-content \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <tu_api_key>" \
  -d '{"text": "un articulo largo de al menos 300 caracteres..."}'
```

**Response 200 — texto clasificado**

```json
{ "verdict": "real", "label": "REAL", "confidence": 0.93, "raw_label": "REAL" }
```

**Response 200 — texto corto (< 300 caracteres), no se clasifica**

```json
{ "verdict": "no_content", "label": "UNKNOWN", "confidence": 0.0 }
```

---

### `GET /cache/stats`

```bash
curl http://localhost:8000/cache/stats -H "X-API-Key: <tu_api_key>"
```

```json
{ "entries": 12, "valid": 9, "ttl_seconds": 600, "max_size": 500 }
```

### `DELETE /cache`

```bash
curl -X DELETE http://localhost:8000/cache -H "X-API-Key: <tu_api_key>"
```

```json
{ "cleared": 12 }
```

---

## Códigos de error

| Código | Cuándo | Contrato |
|---|---|---|
| `422` | Body inválido o campo faltante (Pydantic) | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` (formato estándar de FastAPI) |
| `403` | `API_KEY` configurada en el servidor y el header `X-API-Key` falta o no coincide | `{"detail": "API key inválida o ausente"}` |
| `429` | Más de 30 solicitudes/60s a `/predict` o `/analyze-content` desde la misma IP | `{"error": "Demasiadas solicitudes. Intenta de nuevo en 1 minuto."}`, header `Retry-After: 60` |
| `500` | Excepción no prevista fuera de los puntos con manejo controlado (`_safe()`, try/except por servicio externo) | `{"error": "Error interno del servidor", "detail": "..." }` — `detail` es `null` si `ENVIRONMENT=production` |

Ejemplo de `422` (validación de `url`):

```bash
curl -X POST http://localhost:8000/predict -d '{"url": "no-es-una-url"}'
```

```json
{
  "detail": [
    { "loc": ["body", "url"], "msg": "Value error, La URL debe comenzar con http:// o https://", "type": "value_error" }
  ]
}
```

## Probar sin escribir código

1. Levantar el backend: `venv\Scripts\uvicorn backend.app.main:app --reload`
2. Abrir `http://localhost:8000/docs` en el navegador
3. Expandir cualquier endpoint → **Try it out** → completar el body → **Execute**

Para Postman: **Import → Link** → `http://localhost:8000/openapi.json` importa los 7 endpoints con sus schemas ya tipados.
