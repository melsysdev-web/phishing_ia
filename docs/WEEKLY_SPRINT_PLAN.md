# 📋 Weekly Sprint Plan (Semana 1)
**Fechas**: 2026-08-18 a 2026-08-24  
**Estado Actual**: 316 tests ✅, VT quota protection ✅, Main branch limpio ✅

---

## 🎯 Objetivos Semana 1

1. **Arreglar deprecation warnings** (30 min)
2. **Limpiar linting issues** (15 min)
3. **Stress testing** (2 horas)
4. **Validar deployment en Render** (2 horas)
5. **Implementar OpenTelemetry básico** (2 horas)
6. **Documentar performance baselines** (1 hora)

**Total**: ~8 horas de trabajo

---

## ☑️ Tareas Diarias

### 📅 Lunes 2026-08-18 (Hoy)

**Tarea 1: Arreglar datetime.utcnow() deprecated (30 min)**
```bash
git checkout -b fix/datetime-deprecation
```

**Archivos a modificar**:
- `backend/app/core/quota_circuit.py` (línea 22, 29, 32)

**Cambio**:
```python
# Antes
from datetime import datetime, timedelta
self.day_start = datetime.utcnow()

# Después
from datetime import datetime, timezone, timedelta
self.day_start = datetime.now(timezone.utc)
```

**Tests**: `pytest backend/tests/test_quota_circuit.py -v`

**Commit**:
```
fix: replace datetime.utcnow() with timezone-aware datetime.now(UTC)
```

---

**Tarea 2: Limpiar linting en extended_cache.py (15 min)**
```bash
git checkout -b fix/linting-cleanup
```

**Cambios**:
1. Remover imports no usados: `from datetime import datetime, timedelta`
2. Cambiar `except sqlite3.Error as e:` → `except sqlite3.Error:`

**Verificar**:
```bash
python -m ruff check backend/app/utils/extended_cache.py
```

**Commit**:
```
fix: clean up unused imports and variables in extended_cache
```

---

### 📅 Martes 2026-08-19

**Tarea 3: Implementar stress tests (2 horas)**

**Archivo nuevo**: `tests/test_stress_basic.py`

```python
import concurrent.futures
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_stress_10_concurrent_requests():
    """Básico: 10 requests concurrentes al /predict."""
    urls = [f"http://phishing-{i}.example.com" for i in range(10)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        start = time.time()
        futures = [
            executor.submit(client.post, "/predict", json={"url": url})
            for url in urls
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        elapsed = time.time() - start
    
    # Assertions
    assert len(results) == 10
    success_count = sum(1 for r in results if r.status_code == 200)
    assert success_count >= 8  # al menos 80% éxito
    print(f"✅ 10 requests en {elapsed:.2f}s = {10/elapsed:.1f} req/s")

def test_stress_25_concurrent_requests():
    """Moderado: 25 requests concurrentes."""
    # Similar a anterior pero 25 requests
    pass

def test_analyze_content_stress():
    """Stress en /analyze-content endpoint."""
    texts = [f"This is fake news about politics {i}" for i in range(10)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(client.post, "/analyze-content", json={"text": text})
            for text in texts
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    assert len(results) == 10
    print(f"✅ Analyze-content stress complete")
```

**Ejecutar**:
```bash
pytest tests/test_stress_basic.py -v -s
```

**Commit**:
```
test: add basic stress testing suite for concurrent requests
```

---

### 📅 Miércoles 2026-08-20

**Tarea 4: Validación deployment Render (2 horas)**

**Checklist**:
- [ ] Fork repo a Render
- [ ] Configurar env vars:
  - VIRUSTOTAL_API_KEY
  - SAFE_BROWSING_API_KEY
  - FACT_CHECK_API_KEY
  - API_KEY (opcional para dev)
  - ENVIRONMENT=development
- [ ] Set Dockerfile path: `backend/Dockerfile`
- [ ] Trigger deploy manual
- [ ] Medir cold start (esperado: 60-90s)
- [ ] Test endpoint: `curl https://<service>.onrender.com/health`
- [ ] Verificar logs en Render

**Documentar en**: `docs/DEPLOYMENT_VALIDATION.md`

```markdown
# Validación Render 2026-08-20

## Cold Start Time
- Inicio: 14:23 UTC
- Primer request exitoso: 14:24 UTC
- **Duration: 61 segundos** ✅

## Test Results
- GET /health → 200 OK ✅
- GET /metadata → 200 OK ✅
- POST /predict → 200 OK (5.2s) ✅

## Environment
- Python: 3.12.3
- FastAPI: 0.136.3
- Models: Downloaded from HuggingFace (no local cache)
```

**Commit** (en rama aparte si hay cambios):
```
docs: document Render deployment validation results
```

---

### 📅 Jueves 2026-08-21

**Tarea 5: OpenTelemetry básico (2 horas)**

**Archivo nuevo**: `backend/app/core/tracing.py`

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def init_tracing(app, jaeger_host: str = "localhost", jaeger_port: int = 6831):
    """Initialize distributed tracing with Jaeger."""
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )
    
    trace_provider = TracerProvider()
    trace_provider.add_span_processor(SimpleSpanProcessor(jaeger_exporter))
    
    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    return trace_provider
```

**Integración en main.py**:
```python
from backend.app.core.tracing import init_tracing

# Después de crear la app
if settings.environment == "development":
    init_tracing(app)
```

**docker-compose actualizado** (para local testing):
```yaml
version: '3.8'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "6831:6831/udp"
      - "16686:16686"  # Jaeger UI
```

**Test**:
```bash
docker-compose up jaeger &
pytest backend/tests/ -v
# Abrir http://localhost:16686 → buscar "phishing_api"
```

**Dependencias** (agregar a requirements-dev.txt):
```
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-exporter-jaeger==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-requests==0.42b0
```

**Commit**:
```
feat: add distributed tracing with OpenTelemetry/Jaeger
```

---

### 📅 Viernes 2026-08-22

**Tarea 6: Performance baselines (1 hora)**

**Archivo nuevo**: `docs/PERFORMANCE_BASELINES.md`

---

### 📅 Próxima Semana (Extension Fixes)

**Agregar después de Viernes si hay tiempo, o Semana 2**

#### Tarea 7: Extension Critical Fixes (3 horas)

**Contexto**: Chrome extension tiene 13 issues identificados. 4 son críticos.

**P0 - Hardcoded Backend URL (30 min)**

**File**: `extension/services/api_client.js:1`

Current:
```javascript
const _DEFAULT_URL = "https://phishing-ia-2.onrender.com";
```

Fix:
```javascript
const _DEFAULT_URL = "http://localhost:8000";

async function _config() {
  return new Promise(resolve => {
    chrome.storage.local.get(
      { backendUrl: _DEFAULT_URL, apiKey: "" },
      resolve
    );
  });
}
```

**P1 - Missing extractFromActivePage() Function (45 min)**

**File**: `extension/sidebar/sidebar.js`

Current:
```javascript
document.getElementById("extractPageBtn")
  .addEventListener("click", extractFromActivePage);  // ❌ Function not defined
```

Fix - Add function:
```javascript
async function extractFromActivePage() {
  try {
    const tabs = await chrome.tabs.query({
      active: true,
      currentWindow: true
    });
    const tabId = tabs[0].id;

    const result = await chrome.scripting.executeScript({
      target: { tabId },
      function: extractMainText,
    });

    const text = result[0]?.result || "";
    document.getElementById("contentTextarea").value = text;
    updateCharCount();
  } catch (err) {
    showError("No se pudo extraer el contenido de la página.");
  }
}

function extractMainText() {
  const clone = document.body.cloneNode(true);
  clone.querySelectorAll("script, style").forEach(el => el.remove());
  return clone.innerText.slice(0, 5000);
}
```

**Update manifest.json permissions**:
```json
"permissions": ["storage", "sidePanel", "clipboardRead", "scripting", "activeTab"]
```

**P1 - Better Error Messages (30 min)**

**Files**: `popup.js:79`, `sidebar.js`

Add error message mapping:
```javascript
const ERROR_MESSAGES = {
  429: "Demasiadas solicitudes. Espera un minuto.",
  404: "El servidor no está disponible.",
  500: "Error en el servidor.",
  timeout: "La solicitud tomó demasiado tiempo.",
};

function getErrorMessage(err) {
  if (err.name === "AbortError") return ERROR_MESSAGES.timeout;
  const status = err.status || err.statusCode;
  return ERROR_MESSAGES[status] || err.message || "Error desconocido.";
}
```

Update error handlers to use it.

**P1 - Connection Health Check (45 min)**

**New file**: `extension/background/health_check.js`

```javascript
// Check connection on install
chrome.runtime.onInstalled.addListener(async () => {
  try {
    await ApiClient.testConnection();
    chrome.storage.local.set({ backendConnected: true });
  } catch {
    chrome.storage.local.set({ backendConnected: false });
  }
});

// Periodic health check every 5 minutes
chrome.alarms.create("healthCheck", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "healthCheck") {
    try {
      await ApiClient.testConnection();
      chrome.storage.local.set({ backendConnected: true });
    } catch {
      chrome.storage.local.set({ backendConnected: false });
    }
  }
});
```

Update manifest.json:
```json
"permissions": [..., "alarms"]
```

**Testing**:
- [ ] Popup: Analyze URL → result displays
- [ ] Sidebar: Extract page button → text populated
- [ ] Enter content → analyzes without error
- [ ] Disable backend → shows user-friendly error
- [ ] Re-enable backend → works again
- [ ] Close/reopen popup → history persists

**Commit**: "fix: extension critical issues (hardcoded URL, missing function, error messages, health checks)"

```markdown
# Performance Baselines - 2026-08-22

## SLA Targets (p95)

| Endpoint | Target | Current | Status |
|----------|--------|---------|--------|
| /health | <100ms | 45ms | ✅ |
| /predict (cached) | <500ms | 420ms | ✅ |
| /predict (uncached) | <5s | 3.8s | ✅ |
| /analyze-content | <2s | 1.2s | ✅ |

## Benchmark Results

### Test: 10 concurrent /predict requests
- Throughput: 2.6 req/s
- Latency p50: 1200ms
- Latency p95: 3400ms
- Cache hit ratio: 60%

### Test: Cache statistics
- Redis hits: N/A (not deployed yet)
- SQLite hits: 120 entries
- Cache size: 1.2 MB
```

**Script para generar baselines**:
```bash
# benchmark.py
from backend.app.main import app
from fastapi.testclient import client
import time
import statistics

client = TestClient(app)
latencies = []

for i in range(20):
    start = time.time()
    response = client.post("/predict", json={"url": "http://example.com"})
    latencies.append((time.time() - start) * 1000)

print(f"Latency p50: {statistics.median(latencies):.1f}ms")
print(f"Latency p95: {sorted(latencies)[int(len(latencies) * 0.95)]:.1f}ms")
```

**Ejecutar**:
```bash
python benchmark.py > docs/PERFORMANCE_BASELINES.md
```

**Commit**:
```
docs: add performance baselines and SLA targets
```

---

### 📅 Sábado-Domingo (Buffer/Review)

**Actividades**:
- [ ] Review de todos los commits
- [ ] Ejecutar full test suite: `pytest -v`
- [ ] Verificar no hay breaking changes
- [ ] Preparar PR summary

---

## 🔄 Pull Request Summary (Final de Semana)

**Title**: "Week 1 improvements: deprecations, stress tests, tracing, baselines"

**Description**:
```markdown
## Summary
- ✅ Fixed datetime deprecation warnings (Python 3.13 compatibility)
- ✅ Cleaned up linting issues in extended_cache.py
- ✅ Added stress testing suite (concurrent request benchmarks)
- ✅ Validated Render deployment (60s cold start achieved)
- ✅ Implemented distributed tracing (OpenTelemetry/Jaeger)
- ✅ Documented performance baselines and SLA targets

## Tests
- 316 tests passing ✅
- New stress tests: 3
- Coverage maintained at current levels

## Checklist
- [x] All linting passes (ruff)
- [x] Tests pass locally
- [x] Documentation updated
- [x] No breaking changes
```

---

## 📊 Métricas de Éxito Semana 1

| Métrica | Target | Alcanzado |
|---------|--------|-----------|
| Deprecation warnings | 0 | - |
| Linting errors | 0 | - |
| Stress test pass rate | >80% | - |
| Cold start Render | <90s | - |
| Tracing instrumented | Yes | - |
| Performance documented | Yes | - |

---

## 📌 Notas Importantes

1. **Orden de commits**: Cada tarea debe ser un commit separado y atomico
2. **Testing**: Ejecutar `pytest` después de cada cambio
3. **No merges a main**: Todos los cambios en ramas, luego 1 PR al final
4. **Documentación**: Actualizar CLAUDE.md si hay cambios significativos
5. **Render deploy**: Es solo para validación, no production aún

---

## ⚠️ Riesgos Identificados

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|-----------|
| Render deploy falla | Baja | Usar env dev, no cambiar config |
| Stress tests timeout | Media | Usar 10-25 requests, no 100+ |
| Jaeger no se inicia | Baja | Usar docker-compose, logs |

---

## 📞 Blockers Potenciales

- ¿Tienes credenciales Render acceso?
- ¿Jaeger en local funciona con el VPN?
- ¿Hay restricciones en requirements.txt?

