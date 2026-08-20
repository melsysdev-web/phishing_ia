# 🚀 Redeploy from Scratch — Render Guide

**Date**: 2026-08-20  
**Status**: Ready for clean Render deployment  
**Contains**: Latest stability improvements + VT quota optimization

---

## Pre-Deployment Checklist

### ✅ Code Status
- [x] All changes committed to `feature/extension-ui-redesign-anime`
- [x] Extension stability improvements (defensive code)
- [x] VT quota optimization (circuit breaker + extended cache)
- [x] 316 tests passing locally
- [x] Pre-commit checks passed (linting + security tests)

### ✅ API Keys Ready
Gather before starting deployment:
- [ ] `VIRUSTOTAL_API_KEY` (from virustotal.com)
- [ ] `SAFE_BROWSING_API_KEY` (from Google Console)
- [ ] `FACT_CHECK_API_KEY` (from Google Console)
- [ ] Generate new `API_KEY`: 
  ```powershell
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

---

## Step 1: Delete Old Service (If Exists)

⚠️ **Only if redeploying over existing service**

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click your old web service (if exists)
3. → **Settings** (bottom left)
4. → **Delete Web Service**
5. Confirm deletion

---

## Step 2: Create New Web Service

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. **Connect GitHub**:
   - Select repo: `phishing_ia`
   - Branch: `feature/extension-ui-redesign-anime` ← **IMPORTANT**

4. **Configure Service**:
   - **Name**: `phishing-ia` (or unique name)
   - **Environment**: `Docker`
   - **Region**: `Oregon` (default, US-based)
   - **Dockerfile path**: `backend/Dockerfile` ← **CRITICAL**
   - **Auto-deploy**: ✅ Enable (auto-deploy on push)

5. **Click "Create Web Service"**

---

## Step 3: Add Environment Variables

⏳ **Wait for initial deployment attempt** (~2-3 min)

Then:

1. Go to dashboard → Your service → **Settings**
2. Scroll to **"Environment"** section
3. Add each variable (one at a time):

```
VIRUSTOTAL_API_KEY = <your_key>
SAFE_BROWSING_API_KEY = <your_key>
FACT_CHECK_API_KEY = <your_key>
API_KEY = <generated_key>
FORWARDED_ALLOW_IPS = *
ENVIRONMENT = production
```

4. After each add, service auto-redeploys (~5-10 min)
5. **Watch Logs tab** for `"healthy"` message

---

## Step 4: Monitor First Build (60-90 seconds)

Go to **Logs** tab. You should see:

```
Building Docker image...
Installing dependencies...
Downloading models from HuggingFace Hub (821 MB)...
  - random_forest_v2.pkl (25 MB)
  - roberta_phishing_new/ (317 MB)
  - roberta_content/ (479 MB)
Starting uvicorn...
Application startup complete [healthy]
```

⚠️ **If it takes >2 minutes**: Models downloading is normal, let it finish.

❌ **If you see errors**:
- Check all env vars are set
- Check GitHub repo is public (or Render has access)
- Manually restart in Render dashboard

---

## Step 5: Test the Deployment

```powershell
# Replace with your Render service URL
$url = "https://phishing-ia.onrender.com"

# Test liveness
curl "$url/health"
# Should return: {"status": "healthy"}

# Test API
curl -X POST "$url/predict" `
  -H "Content-Type: application/json" `
  -d '{"url":"https://google.com"}' `
  -H "X-API-Key: <your_API_KEY_here>"
# Should return full analysis with risk score
```

---

## Step 6: Update Extension

1. Open Chrome with extension loaded
2. Right-click extension → **Options**
3. Set **Backend URL**: `https://phishing-ia.onrender.com`
4. If you set `API_KEY`: paste it in options too
5. Save
6. Test: Analyze a URL in popup

---

## Step 7: Merge to Main (Optional)

Once verified on staging:

```powershell
git checkout main
git pull origin main
git merge feature/extension-ui-redesign-anime
git push origin main
```

This enables auto-deploy for future pushes to main.

---

## Troubleshooting

### Service Won't Start ("Build Failed")

**Check**:
1. Dockerfile path is `backend/Dockerfile` (not `Dockerfile`)
2. GitHub repo is accessible
3. No syntax errors in code

**Solution**:
```powershell
# Verify Dockerfile exists locally
Test-Path "backend/Dockerfile"
```

### Models Not Downloading ("Timeout after 30 min")

**Cause**: HuggingFace Hub slow or blocked

**Solution**:
1. In Render settings → **Auto-Deploy** → Disable
2. Manually restart in dashboard (→ **Manual Restart**)
3. Wait 2-3 min
4. If still fails: contact HuggingFace or use local mirror

### "Unhealthy" Status (Red in Dashboard)

**Check logs for**:
- Missing API keys → Add to Environment
- Model loading errors → Check logs detail
- Port issues → Should be auto-assigned

**Solution**:
1. Fix issue
2. Commit to GitHub
3. Manual restart in Render dashboard

### API Returns 403 (Auth Required)

**Cause**: `API_KEY` set but extension not sending it

**Solution**:
1. Open extension options
2. Copy `API_KEY` from Render settings
3. Paste into extension options
4. Save and retry

### Extension Popup Blank

**Check**:
1. Backend URL is correct (starts with `https://`)
2. API key matches (if set)
3. Backend is responding to `/health`
4. Open DevTools (F12) in popup → Console for errors

---

## Environment Variables Reference

| Variable | Value | Notes |
|----------|-------|-------|
| `VIRUSTOTAL_API_KEY` | `a1b2c3d4...` | Required |
| `SAFE_BROWSING_API_KEY` | `e5f6g7h8...` | Required |
| `FACT_CHECK_API_KEY` | `i9j0k1l2...` | Required |
| `API_KEY` | `a1b2c3...` (32 hex chars) | Optional (if empty, auth disabled) |
| `FORWARDED_ALLOW_IPS` | `*` | Required for rate-limit IP detection |
| `ENVIRONMENT` | `production` | Required (activates security features) |
| `ALLOWED_ORIGINS` | (comma-separated URLs) | Optional (for CORS) |
| `MODELS_DIR` | `/models` | Optional (usually auto) |

---

## Performance Expectations

| Metric | Value | Notes |
|--------|-------|-------|
| Cold start | 60-90s | First request after 15 min idle |
| Warm start | <1s | Subsequent requests |
| URL analysis | 2-5s | Depends on backend APIs |
| Content analysis | 5-10s | ML model inference time |
| Cache hit | <500ms | Repeat URLs from extended cache |

---

## After Deployment

### ✅ Verify
- [x] Extension connects to backend
- [x] URL analysis works
- [x] Results display correctly
- [x] No 500 errors in console
- [x] Rate limiting working (429 after 30 requests/min)
- [x] VT quota circuit breaker active

### 📊 Monitor
- Watch Render logs for errors
- Check extension console (F12) for API errors
- Monitor Render metrics (CPU, memory, requests)

### 🔄 Updates
To update backend after changes:
```powershell
git push origin feature/extension-ui-redesign-anime
# Render auto-deploys if auto-deploy enabled
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/Dockerfile` | Docker build instructions |
| `backend/requirements.txt` | Python dependencies |
| `backend/app/main.py` | FastAPI entry point |
| `.github/workflows/ci.yml` | GitHub CI (tests before Render deployment) |

---

## Rollback Plan

If deployment fails:

1. **Revert to previous commit**:
   ```powershell
   git revert HEAD
   git push origin feature/extension-ui-redesign-anime
   # Render auto-redeploys with previous working version
   ```

2. **Or delete and recreate**:
   - Delete service in Render dashboard
   - Create new service from stable commit
   - Re-add env vars

---

## Success Criteria

✅ **Deployment successful when**:
- Dashboard shows "Live" status (green)
- Logs show "Application startup complete [healthy]"
- `/health` endpoint returns 200 OK
- Extension connects and analyzes URLs
- No 500 errors in production

---

## Support

**For issues**:
- Check `docs/DEPLOYMENT.md` (detailed technical guide)
- Review Render logs for specific errors
- Verify all env vars are set correctly
- Test backend locally before Render: `venv\Scripts\uvicorn backend.app.main:app`

---

**Ready to deploy!** Follow steps 1-6 above. Estimated time: 15-20 minutes.
