# 🚀 Deployment Guide — Render + Docker

Complete step-by-step guide to deploy the backend on **Render** (serverless Docker platform).

---

## Quick Start (5 Steps)

### 1. Create Web Service on Render

- Go to [dashboard.render.com](https://dashboard.render.com) → **"New +"** → **"Web Service"**
- Connect your GitHub repo (`phishing_ia`)
- Set **Language** to `Docker`
- Set **Dockerfile path** to `backend/Dockerfile` ← **CRITICAL** (Render doesn't auto-detect)
- Enable **"Auto-Deploy"** on push to `main`

### 2. Configure Environment Variables

In Render dashboard → **Settings** → **Environment**, add:

```bash
# External APIs (required)
VIRUSTOTAL_API_KEY=<your_key>
SAFE_BROWSING_API_KEY=<your_key>
FACT_CHECK_API_KEY=<your_key>

# Backend authentication (recommended)
API_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">

# Proxy headers (CRITICAL for rate-limit IP detection)
FORWARDED_ALLOW_IPS=*

# Environment
ENVIRONMENT=production
```

**How to get API keys:**
- **VirusTotal**: https://www.virustotal.com/gui → Sign up → API section
- **Google Safe Browsing**: https://console.developers.google.com → API Safe Browsing v4
- **Fact Check API**: https://console.developers.google.com → API Fact Check Tools

### 3. Monitor Logs

- Open Render dashboard → **Logs** tab
- Wait for `"healthy"` message (~60-90s first time, models download from HuggingFace)
- Service is ready at `https://<service-name>.onrender.com`

### 4. Test the API

```bash
curl https://<service-name>.onrender.com/health
curl https://<service-name>.onrender.com/metadata
```

### 5. Update Extension

- Extension options page → Backend URL → `https://<service-name>.onrender.com`
- If you set `API_KEY` → also paste it in options page

---

## Technical Details

### Docker Build

- **Dockerfile Path**: `backend/Dockerfile` (must be explicit — Render doesn't auto-detect)
- **Base Image**: `python:3.12-slim`
- **Model Download**: During build, `backend/Dockerfile` downloads models from HuggingFace Hub (`mel3601/phishing-ia-models`)
- **Startup**: `uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}`

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `VIRUSTOTAL_API_KEY` | VirusTotal threat intel | `abc123...` |
| `SAFE_BROWSING_API_KEY` | Google Safe Browsing API | `def456...` |
| `FACT_CHECK_API_KEY` | Google Fact Check Tools API | `ghi789...` |
| `API_KEY` | Backend authentication (X-API-Key header) | `a7f3c9e2b1d4f6a8c5e2b9d1f4a7c3e5...` |
| `FORWARDED_ALLOW_IPS` | Trust X-Forwarded-For from proxy | `*` (Render safe) |
| `ENVIRONMENT` | `production` or `development` | `production` |
| `ALLOWED_ORIGINS` | Extra CORS origins (comma-separated) | `https://example.com,https://other.com` |
| `MAX_CONCURRENT_ANALYSES` | Analyses allowed at once (shared by `/predict` and `/analyze-content`) | `1` (do not raise on 512 MB) |
| `ANALYSIS_QUEUE_TIMEOUT` | Seconds queued before a 503 | `30` |
| `LOG_LEVEL` | Root log level | `INFO` |

### Models on Render

Models (~821 MB total) are downloaded during Docker build and baked into the image:

- `random_forest_v2.pkl` (25 MB)
- `roberta_phishing_new/` (317 MB)
- `roberta_content/` (479 MB)

Stored at `/models` (persistent during container lifetime).

---

## Performance Characteristics

### Cold Start (~60-90 seconds)

After 15 minutes of inactivity, Render suspends free containers. Next request triggers:

1. Container spin-up (~5-10s)
2. Model loading to memory (~10-20s, lazy-loaded)
3. FastAPI startup (~5s)
4. **Total**: ~60-90s

This is **expected and OK** for low-traffic use.

### Warm Requests (~500-2000ms)

Once models are loaded:
- URL feature extraction: ~100ms
- HTML fetch (if needed): +500-1500ms
- ML inference (parallel): +200-500ms
- Risk aggregation: ~100ms

### Scaling Notes

Render free tier: Single container, no auto-scaling. For production volume, upgrade to **Render Pro** or use a load balancer.

---

## Security in Production

### API Key Authentication

If `API_KEY` is set, all requests to `/predict` and `/analyze-content` require:

```bash
curl -H "X-API-Key: your_key_here" \
  https://<service>.onrender.com/predict \
  -d '{"url": "https://example.com"}' \
  -H "Content-Type: application/json"
```

Key comparison uses `hmac.compare_digest()` (not `==`) to prevent timing side-channels.

### CORS

- ✅ Allows `chrome-extension://[a-z]{32}` (Chrome extensions)
- ✅ Allows `localhost` and `127.0.0.1` (local development)
- ❌ Blocks random web origins by default

To add origins: set `ALLOWED_ORIGINS=https://your-site.com` in env vars.

### Rate Limiting

- **30 requests / 60 seconds per client IP**
- Grouped by real visitor IP (thanks to `FORWARDED_ALLOW_IPS=*`)
- Response: `429 Too Many Requests` with `Retry-After: 60`

### Error Messages

- **Production** (`ENVIRONMENT=production`): Error responses omit `detail` to avoid leaking implementation details
- **Development**: Full traceback for debugging

### SSRF Protection

- `HtmlFetcher.get_html()` validates all hostnames against private IP ranges (RFC1918, loopback, link-local, reserved, multicast)
- `ssrf_guard.py` patches urllib3 at the socket level to prevent DNS rebinding attacks

---

## Troubleshooting

### "Dockerfile path not found"

**Cause**: Render looking in repo root

**Fix**: Explicitly set **Dockerfile path** to `backend/Dockerfile` in Render dashboard

---

### `/health` returns 503

**Cause**: Container is still initializing; models downloading from HuggingFace

**Fix**: Wait 30-60 seconds. Models load lazily on first `/predict` call, not at startup.

---

### All users share rate-limit bucket

**Cause**: `FORWARDED_ALLOW_IPS` not configured

**Fix**:
1. Open Render dashboard → **Settings** → **Environment**
2. Add/update: `FORWARDED_ALLOW_IPS=*`
3. Click **Save** (auto-triggers redeploy)

---

### API_KEY rejected (403 Forbidden)

**Cause**: Key mismatch, typo, or wrong header

**Verify**:
- Header name is exactly `X-API-Key` (case-sensitive)
- Key value matches exactly (no leading/trailing spaces)
- Key was generated with `secrets.token_hex(32)` on your machine

---

### Models not loading (all signals degrade)

**Cause**: HuggingFace Hub unavailable or repo not public

**Check**:
- Repo `mel3601/phishing-ia-models` is public on HuggingFace
- Container has internet access

**Note**: Signals degrade gracefully via `_safe()`. Backend still runs, just without ML scores. This is OK for dev, not for production.

---

## Local Development

To test deployment locally without Render:

```bash
# Build Docker image
docker build -f backend/Dockerfile -t phishing-backend .

# Run with env vars
docker run -p 8000:8000 \
  -e VIRUSTOTAL_API_KEY=test \
  -e SAFE_BROWSING_API_KEY=test \
  -e FACT_CHECK_API_KEY=test \
  -e API_KEY=test-key \
  -e FORWARDED_ALLOW_IPS='127.0.0.1' \
  phishing-backend

# Test
curl http://localhost:8000/health
```

Or use `docker-compose`:

```bash
docker compose up backend
```

---

## Monitoring (Future)

### Prometheus Metrics

`/metrics` endpoint (unauthenticated) is available for Prometheus scraping:

```
GET https://<service>.onrender.com/metrics
```

Exposes:
- `http_requests_total` — request count
- `http_request_duration_seconds` — latency histogram
- `app_startup_duration_seconds` — boot time

### Setting Up Monitoring

For production: integrate with **Sentry**, **CloudWatch**, **Datadog**, or **Grafana**.

Render free tier doesn't include monitoring; use third-party services.

---

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` automatically:

1. **On push/PR to `main`**: Runs `pytest`, `ruff check`
2. **If tests pass**: Render auto-deploys (if enabled)

No manual setup needed — it's automatic.

---

## Pre-Deploy Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Code linted (`ruff check .`)
- [ ] `.env.example` updated with new vars
- [ ] `backend/Dockerfile` exists
- [ ] Have API keys (VirusTotal, Safe Browsing, Fact Check)
- [ ] Generated `API_KEY` with `secrets.token_hex(32)`
- [ ] Created Web Service on Render
- [ ] Configured all env vars in Render dashboard
- [ ] Set `FORWARDED_ALLOW_IPS=*`

---

## References

- [Render Docs — Docker](https://render.com/docs/docker)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [uvicorn Settings](https://www.uvicorn.org/settings/)
- [HuggingFace Hub Docs](https://huggingface.co/docs/hub/)
