# 🔍 Distributed Tracing Guide

**Framework**: OpenTelemetry + Jaeger  
**Status**: Development environment (auto-enabled when `ENVIRONMENT=development`)

---

## Quick Start

### 1. Start Jaeger (local development)

```bash
docker-compose up jaeger
```

This starts:
- **Jaeger Agent** (UDP port 6831) — receives traces from backend
- **Jaeger UI** (http://localhost:16686) — visualize traces

### 2. Start Backend with Tracing

```bash
ENVIRONMENT=development uvicorn backend.app.main:app --reload
```

The backend will automatically connect to Jaeger on startup:
```
INFO: Tracing initialized: phishing-api → localhost:6831
```

### 3. Make API Calls

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"url": "http://example.com"}'
```

### 4. View Traces

Open **http://localhost:16686** and search for:
- Service: `phishing-api`
- Look for spans like:
  - `POST /predict`
  - `GET http://example.com` (HTML fetch)
  - `phishing_service.analyze`

---

## What Gets Traced

### Auto-Instrumented (via OpenTelemetry)

| Component | Traced | What |
|-----------|--------|------|
| **FastAPI** | ✅ | HTTP requests (path, method, status, latency) |
| **requests library** | ✅ | External API calls (GET/POST, URL, status) |
| **ThreadPool** | ❌ | (Custom implementation, not instrumented) |

### Manual Spans (TODO - Phase 2)

- `phishing_service.analyze()` — full pipeline
- `RandomForestPredictor.predict()` — ML inference
- `RobertaPredictor.predict()` — NLP inference
- `VirusTotalService.analyze()` — VT API call
- Cache hits/misses

---

## Trace Example

### Single `/predict` Request

```
POST /predict (400ms total)
├── extract_url_features (2ms)
├── [Parallel Group 1] (180ms)
│  ├── GET whois (100ms)
│  ├── GET http://phishing.example.com (45ms)
│  ├── POST virustotal/analyze (40ms)
│  ├── POST safebrowsing/lookup (30ms)
│  └── RobERTa prediction (15ms)
├── [Sequential Group 2] (150ms)
│  ├── RandomForest prediction (120ms)
│  └── RiskEngine scoring (30ms)
└── Return response + cache (2ms)
```

In Jaeger UI:
- Each subprocess shows as a separate span
- Click spans to see attributes (URL, status, error details)
- Timeline shows where time was spent

---

## Configuration

### Enable/Disable Tracing

**Environment variable**:
```bash
# Auto-enable for development
ENVIRONMENT=development  # → tracing on

# Auto-disable for production
ENVIRONMENT=production   # → tracing off
```

**Manual override** (in code):
```python
from backend.app.core.tracing import init_tracing

# Explicitly enable
trace_provider = init_tracing(app, enabled=True)

# Explicitly disable
trace_provider = init_tracing(app, enabled=False)
```

### Jaeger Connection

```python
# Default (localhost)
init_tracing(app)

# Custom host/port
init_tracing(
    app,
    jaeger_host="jaeger.example.com",
    jaeger_port=6831,
    service_name="phishing-api-prod"
)
```

---

## Installation (Optional)

Tracing is optional. If OpenTelemetry is not installed, the app continues without tracing (logs a warning).

To enable tracing locally:

```bash
pip install -r requirements-tracing.txt
```

Or manually:
```bash
pip install \
  opentelemetry-api==1.21.0 \
  opentelemetry-sdk==1.21.0 \
  opentelemetry-exporter-jaeger==1.21.0 \
  opentelemetry-instrumentation-fastapi==0.42b0 \
  opentelemetry-instrumentation-requests==0.42b0
```

---

## Use Cases

### 1. Debug Slow Requests

**Problem**: `/predict` taking 10+ seconds

**Solution**:
1. Make the slow request
2. Open Jaeger UI → search for `/predict`
3. Look for which span is taking longest
4. Optimize that component

Example:
- If `GET http://...` span is 5s → HTML fetch is slow
- If `RandomForest` span is 3s → model inference is slow
- If total is fast but latency reported high → check network latency

### 2. Analyze Concurrency Issues

**Problem**: API slows down under concurrent load

**Solution**:
1. Run `pytest tests/test_stress_basic.py`
2. In Jaeger, filter by: `process.tags.thread_name`
3. See how threads are interleaved and blocked

### 3. Monitor External API Failures

**Problem**: VirusTotal returning 429s

**Solution**:
1. Trace shows `POST virustotal/analyze` → 429 (Rate Limit)
2. Set alerts when VT span status != 200
3. Monitor quota in real-time

---

## Jaeger UI Guide

### Search Tab

```
Service: phishing-api
Operation: POST /predict
Tags: http.status_code=200
Limit Results: 20
```

Click **Find Traces** to see matching requests.

### Trace Details

For each trace:
- **Timeline view**: See span order and duration
- **Trace Statistics**: Min/max/avg latency
- **Span Details**: Click a span to see:
  - Duration
  - Status (success/error)
  - Tags (URL, status code, etc)
  - Logs (error messages)

### Latency Comparison

Compare two traces side-by-side:
1. Click "Compare" button
2. Select two traces
3. See which endpoints differ in speed

---

## Performance Impact

**Overhead** (with tracing enabled):
- CPU: +2-3% (span creation + serialization)
- Memory: +10-15 MB (batch buffering)
- Latency: <5ms per request (negligible)

**With batching** (default):
- Traces are batched and sent async → minimal blocking
- Jaeger agent is lightweight → <50 MB RAM

**Production deployment**:
- Tracing should be disabled (ENVIRONMENT=production)
- If needed, use sampling: `traces_sample_rate=0.1` (10%)

---

## Troubleshooting

### Traces Not Appearing

**Check 1**: Is backend sending traces?
```bash
# Look for log line on startup
INFO: Tracing initialized: phishing-api → localhost:6831
```

**Check 2**: Is Jaeger running?
```bash
# Should be healthy
curl http://localhost:16686/api/services
# Returns: {"data":["phishing-api"], "total":1, "limit":10}
```

**Check 3**: Check network connectivity
```bash
# From backend container/host
nc -u -z localhost 6831
# Should succeed silently
```

### "OpenTelemetry not installed" Warning

Install it:
```bash
pip install -r requirements-tracing.txt
```

Or for development:
```bash
pip install opentelemetry-sdk opentelemetry-exporter-jaeger
```

### Jaeger Agent Crashes on Port 6831

**Problem**: Port 6831 (UDP) already in use

**Solution**:
```bash
# Find what's using it
lsof -i :6831

# Or use different port in docker-compose.yml
ports:
  - "6832:6831/udp"  # Map external 6832 to container 6831
```

---

## Advanced: Custom Spans

To trace custom business logic (Phase 2):

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("analyze_url") as span:
    span.set_attribute("url", url)
    span.set_attribute("method", "rf_prediction")
    
    result = model.predict(features)
    
    span.set_attribute("confidence", result.confidence)
```

---

## Monitoring & Alerts (Production)

Once Jaeger is running, set up alerts via Prometheus:

```yaml
# prometheus/prometheus.yml
scrape_configs:
  - job_name: jaeger
    static_configs:
      - targets: ['localhost:14269']  # Jaeger metrics endpoint
```

Monitor:
- `jaeger_agent_spans_received_total` → dropped spans?
- `jaeger_agent_spans_processed_total` → healthy throughput?

---

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/)
- [Jaeger Documentation](https://www.jaegertracing.io/)
- [FastAPI Instrumentation](https://opentelemetry.io/docs/instrumentation/python/libraries/fastapi/)

---

**Last Updated**: 2026-08-18  
**Status**: Development only (auto-disabled in production)
