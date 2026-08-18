# 🚀 Render Deployment Checklist

**Status**: Ready to Deploy  
**Date Started**: 2026-08-25  
**Target**: Production deployment with cold start <90s

---

## Pre-Deployment Checks

- [ ] Branch is clean (`git status`)
- [ ] All 324 tests passing locally
- [ ] No linting errors
- [ ] `.env` file has all required keys
- [ ] Docker builds successfully locally
- [ ] Extension hardcoded URL is set to `http://localhost:8000` (will update after deploy)

---

## Step 1: Create Render Web Service

### 1.1 Create New Service

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Select **"Public Git Repository"**
4. Connect GitHub account (if not already connected)
5. Select repository: `phishing_ia` (or your fork)
6. Choose branch: `main`
7. Click **"Connect"**

### 1.2 Configure Service

**Name**: `phishing-ia` (or your preferred name)

**Environment**: Docker

**Docker Dockerfile path**: `backend/Dockerfile`

**Build command**: (leave empty - auto-detected)

**Start command**: (leave empty - auto-detected from Dockerfile)

**Instance Type**: Standard (1 vCPU, 512 MB RAM, $7/month)

**Auto-Deploy**: ON (deploy on every push to main)

---

## Step 2: Configure Environment Variables

Click **"Environment"** tab and add these variables:

```
Key: ENVIRONMENT
Value: production

Key: VIRUSTOTAL_API_KEY
Value: [your-VT-API-key]

Key: SAFE_BROWSING_API_KEY
Value: [your-Google-Safe-Browsing-key]

Key: FACT_CHECK_API_KEY
Value: [your-Google-Fact-Check-key]

Key: API_KEY
Value: [your-extension-api-key] (optional, leave blank for no auth)

Key: FORWARDED_ALLOW_IPS
Value: *

Key: MODELS_DIR
Value: /models
```

**How to get API keys**:
- VirusTotal: https://www.virustotal.com/gui/settings/api
- Google Safe Browsing: https://console.cloud.google.com/
- Google Fact Check: https://console.cloud.google.com/

---

## Step 3: Monitor Deployment

### 3.1 Watch the Build

1. Click **"Logs"** tab
2. Wait for build to complete (typically 60-90 seconds)
3. Look for messages:
   ```
   Downloading models from HuggingFace...
   Loaded random_forest_v2.pkl
   Loaded roberta_phishing_new
   Loaded roberta_content
   Startup complete
   ```

### 3.2 Record Cold Start Time

When you see "Startup complete", note the time:
- **Start time**: [deployment click time]
- **End time**: [startup complete time]
- **Duration**: [difference] seconds

**Expected**: 60-90 seconds ✅

---

## Step 4: Test Live Endpoints

Once deployment is complete, you'll get a URL like:
```
https://phishing-ia-xxxxx.onrender.com
```

### 4.1 Test Health Endpoint
```bash
curl https://phishing-ia-xxxxx.onrender.com/health
```
Expected response:
```json
{"status": "healthy"}
```

### 4.2 Test Metadata Endpoint
```bash
curl https://phishing-ia-xxxxx.onrender.com/metadata
```
Expected response:
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

### 4.3 Test Predict Endpoint (requires API key if set)
```bash
curl -X POST https://phishing-ia-xxxxx.onrender.com/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: [your-API-key-if-set]" \
  -d '{"url": "https://google.com"}'
```
Expected response:
```json
{
  "risk_assessment": {
    "score": [0-100],
    "level": "LOW|MEDIUM|HIGH",
    "reasons": [...]
  },
  ...
}
```

---

## Step 5: Configure Custom Domain (Optional)

If you want a custom domain:

1. Click **"Settings"** tab
2. Scroll to **"Custom Domain"**
3. Enter your domain (e.g., `api.phishing-detector.com`)
4. Add DNS records as instructed by Render
5. Wait for SSL certificate (automatic, 5-10 min)

---

## Step 6: Update Extension Configuration

Once Render URL is live:

**File**: `extension/services/api_client.js`

Update production URL:
```javascript
const _PRODUCTION_URL = "https://phishing-ia-xxxxx.onrender.com";
```

---

## Post-Deployment Monitoring

### 6.1 Monitor Logs

1. Click **"Logs"** tab in Render dashboard
2. Watch for:
   - Request patterns
   - Error rates
   - Model loading issues
   - API call successes/failures

### 6.2 Check Metrics

Every hour, verify:
- [ ] Uptime > 99%
- [ ] Response time p95 < 5 seconds
- [ ] No 5xx errors
- [ ] VT API quota usage reasonable

### 6.3 Set Up Alerts (Optional)

Render free tier doesn't have alerts, but you can:
1. Monitor logs manually every few hours
2. Set up a cron job to ping `/health` endpoint
3. Use external monitoring (e.g., UptimeRobot)

---

## Troubleshooting

### Issue: Build fails with "Model not found"

**Solution**:
1. Check logs for HuggingFace download errors
2. Verify internet connectivity in Render's build environment
3. Retry deployment: click **"Manual Deploy"** → **"Deploy latest commit"**

### Issue: Startup times > 120 seconds

**Possible causes**:
- Model files still downloading
- Initial HuggingFace cache warm-up
- SSL certificate generation

**Solution**: Wait longer or check Render logs for details

### Issue: `/predict` returns 500 error

**Check**:
1. API key matches (if `API_KEY` env var is set)
2. External APIs are reachable (VT, Safe Browsing, etc.)
3. Check logs for specific error message

### Issue: Extension can't connect to backend

**Check**:
1. Render URL is correct in `extension/services/api_client.js`
2. CORS is enabled (should be automatic)
3. Extension API key matches backend `API_KEY` if set

---

## Deployment Verification Checklist

- [ ] Render dashboard shows "Live" status
- [ ] Cold start time recorded
- [ ] `/health` returns 200 OK
- [ ] `/metadata` shows all models loaded
- [ ] `/predict` works with valid URL
- [ ] `/analyze-content` works with test text
- [ ] Logs show no error warnings
- [ ] Extension can connect to backend
- [ ] Extension extract button works
- [ ] Performance acceptable (p95 < 5s)

---

## Rollback Plan

If deployment has critical issues:

1. **Quick disable**: Render → Settings → Suspend Service
2. **Revert code**: `git revert HEAD` if needed
3. **Re-deploy**: Click **"Manual Deploy"** on previous working commit
4. **Debug**: Check logs for specific error messages

---

## Performance Baseline (Post-Deploy)

Record these metrics 24 hours after deployment:

| Metric | Target | Actual |
|--------|--------|--------|
| Uptime | >99% | ___ |
| P95 Latency | <5s | ___ |
| P50 Latency | <1s | ___ |
| Error Rate | <1% | ___ |
| VT Calls/day | <500 | ___ |
| Cache Hit Ratio | >50% | ___ |

---

## Next Steps

After successful deployment:

1. ✅ Update extension with production URL
2. ✅ Test extension against production
3. ✅ Document cold start time
4. ✅ Move to Task 6 (Extension Production Config)
5. ✅ Then Task 7 (OT Integration)

---

**Status**: Ready to deploy ✅  
**Estimated Duration**: 2 hours (including build)  
**Risk Level**: Low (reversible, auto-deploy on push)

