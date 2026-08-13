# AI Phishing Detector — Plan de Infraestructura Mínima y Costos

## Metodología

Los números de este documento no son estimaciones a ciegas: se midieron ejecutando el backend real dentro del contenedor Docker definido en `backend/Dockerfile` / `docker-compose.yml` (`docker compose up --build`), con los 3 modelos ML cargados (Random Forest + RoBERTa URL + RoBERTa content), y observando `docker stats` en reposo y bajo carga puntual (`/predict`, `/analyze-content`).

---

## Datos medidos

| Métrica | Valor medido |
|---|---|
| RAM en reposo (sin modelos cargados aún — carga lazy vía `@lru_cache`) | 335 MB |
| RAM pico (los 3 modelos ML cargados en memoria) | **494 MB** |
| CPU en reposo / bajo request puntual | <1% |
| Tiempo de respuesta `/predict` (pipeline completo) | ~2.2–3.2 s |
| Tamaño de `models/` necesario para desplegar | **821 MB** |

---

## Hallazgo: tamaño real de `models/`

Al revisar `models/` se encontró que pesaba originalmente **11 GB**, pero la mayor parte eran checkpoints intermedios de entrenamiento (`checkpoint-*`) que el `Trainer` de HuggingFace guarda automáticamente durante `content_trainer.py` / `trainer.py` y que nunca se limpiaron. `ModelLoader` (`backend/app/roberta/model_loader.py`, `backend/app/random_forest/model_loader.py`) carga los modelos desde la **raíz** de cada carpeta (`config.json` + `model.safetensors` / `.pkl`), nunca desde los subdirectorios `checkpoint-*`.

Se eliminaron esos checkpoints (no usados en inferencia, no versionados en git — `models/` está en `.gitignore`):

| Carpeta eliminada | Tamaño liberado |
|---|---:|
| `models/roberta_content/checkpoint-3045` | 3.2 GB |
| `models/roberta_content/checkpoint-6090` | 3.2 GB |
| `models/roberta_content/checkpoint-9135` | 1.4 GB |
| `models/roberta_phishing_new/checkpoint-10672` | 940 MB |
| `models/roberta_phishing_new/checkpoint-5336` | 940 MB |
| **Total liberado** | **~10.2 GB** |

Tras la limpieza se verificó que el backend sigue funcionando de forma idéntica (`/metadata` reporta los 3 modelos como `true`, `/predict` responde `200`).

**Tamaño real desplegable:**

| Archivo/carpeta | Tamaño |
|---|---:|
| `random_forest_v2.pkl` + `feature_columns_v2.pkl` | 25 MB |
| `roberta_phishing_new/` | 317 MB |
| `roberta_content/` | 479 MB |
| **Total** | **821 MB** |

---

## Plan de infraestructura mínima

**Cómputo**
- Sin GPU — `backend/requirements.txt` fija PyTorch build CPU-only (`--extra-index-url https://download.pytorch.org/whl/cpu`), a diferencia del `requirements.txt` raíz (entrenamiento, CUDA).
- RAM medida en pico ≈ 494 MB. Con margen de seguridad para requests concurrentes (el `RateLimitMiddleware` permite hasta 30 req/min por IP) y evitar OOM bajo carga: **mínimo recomendado 1 GB de RAM**.
- 1 servicio web (`uvicorn`), sin necesidad de múltiples réplicas para el alcance actual (proyecto académico/demo).

**Disco**
- ~821 MB para modelos (tras limpieza) + ~1.5 GB para la imagen base con dependencias (Python 3.12-slim + PyTorch CPU + transformers + scikit-learn).
- Sin base de datos. El cache de resultados es en memoria (`backend/app/utils/url_cache.py`, TTL 10 min, máx. 500 entradas) — se pierde en cada restart del contenedor, lo cual es aceptable para este caso de uso (no es fuente de verdad, solo optimización de latencia).

**Red**
- Tráfico saliente hacia APIs externas: VirusTotal v3, Google Safe Browsing v4, Google Fact Check Tools API, y consultas WHOIS.
- Sin requisitos especiales de ancho de banda — el pipeline procesa una URL a la vez por request, no hay streaming ni archivos grandes en tránsito.

---

## Supuestos

- Tráfico bajo, propio de un proyecto académico/demo — no está dimensionado para producción con carga sostenida real.
- Los modelos se sirven como volumen/disco montado en `/models` (variable `MODELS_DIR`), no horneados dentro de la imagen Docker (`.dockerignore` ya excluye `models/` del build context).
- Sin persistencia de datos entre despliegues más allá de los archivos de modelo — aceptable porque el servicio es *stateless* (cada análisis es independiente, el cache es solo una optimización).
- Sin autenticación de usuarios ni multi-tenancy — la única autenticación es a nivel de servicio (`X-API-Key` opcional, ver `backend/app/core/security.py`).

---

## Costos estimados (Render)

> Cifras de referencia — verificar precios vigentes en render.com/pricing antes de decidir, cambian con el tiempo.

| Opción | RAM | Notas |
|---|---|---|
| **Free tier** | 512 MB | Gratis, pero el pico medido (494 MB) deja **muy poco margen** — riesgo real de OOM bajo cualquier carga concurrente adicional. Además hace *spin down* tras ~15 min de inactividad (cold start de 30–60 s en el siguiente request). No recomendado para una demo en vivo. |
| **Tier pago de entrada** | ≥512 MB garantizados, sin spin down | Recomendado si el servicio debe estar siempre disponible (ej. el día de una evaluación en vivo). Costo histórico ~US$7/mes — confirmar valor actual. |
| **Disco persistente adicional** | — | Con 821 MB reales de modelos, el costo de almacenamiento extra es marginal. Con los 11 GB originales (antes de la limpieza) habría sido un costo notable. |

---

## Riesgos identificados

1. **Margen de RAM ajustado en el free tier**: 494 MB medido vs 512 MB de límite — cualquier pico adicional (ej. varias requests concurrentes, un HTML muy grande a parsear) puede causar un *out-of-memory kill* del proceso.
2. **Cold start en free tier**: tras spin down, el primer request después de inactividad debe re-cargar los 3 modelos ML desde disco antes de poder responder — impacto directo en la demo si el evaluador prueba justo después de un período sin uso.
3. **Modelos no versionados (`models/` en `.gitignore`)**: en un despliegue nuevo hay que garantizar que los archivos de modelo (821 MB) lleguen al volumen montado en `/models` por algún mecanismo (Render Disk, descarga en build, etc.) — no basta con `git push`.
