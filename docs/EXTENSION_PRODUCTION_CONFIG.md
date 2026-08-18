# 🔧 Extension Production Configuration

**Status**: Ready  
**Estimated Time**: 30 minutes  
**Dependencies**: Render deployment URL from Task 5

---

## Overview

After Render deployment, the extension needs to:
1. Use production backend URL instead of localhost
2. Support API key if configured
3. Allow users to configure backend URL in options

---

## Step 1: Update Production URL

**File**: `extension/services/api_client.js`

### Current Code (Lines 1-8)
```javascript
const _DEFAULT_URL = "http://localhost:8000";
const _PRODUCTION_URL = "https://phishing-ia.onrender.com";

async function _config() {
  return new Promise(resolve => {
    chrome.storage.local.get({
      backendUrl: _DEFAULT_URL,
      apiKey: "",
      production: false,
    }, (config) => {
      ...
```

### Update Production URL

Replace `https://phishing-ia.onrender.com` with your actual Render URL:

```javascript
const _PRODUCTION_URL = "https://phishing-ia-XXXXX.onrender.com";
                                          ↑
                                    Your actual ID
```

**How to get your Render URL**:
1. Go to https://dashboard.render.com/
2. Select your web service
3. URL is shown at the top (e.g., `https://phishing-ia-xxxxx.onrender.com`)

---

## Step 2: Test Against Production Backend

### 2.1 Manual Test

1. Open extension popup in Chrome
2. Enter test URL: `https://google.com`
3. Click **"Analizar"** (Analyze)
4. Should see result within 5-10 seconds

**If it works**: ✅ Production backend is reachable

**If it fails**: Check error message
- "Demasiadas solicitudes" → Rate limit hit (wait 1 min)
- "El servidor no está disponible" → Backend offline
- "Acceso denegado" → API key mismatch (if configured)

### 2.2 Test Extract Page

1. Navigate to any webpage
2. Open extension sidebar
3. Go to **"Contenido"** tab
4. Click **"📄 Usar página actual"**
5. Should see page text in textarea

**If works**: ✅ Page extraction works

### 2.3 Test Content Analysis

1. In sidebar, paste some text
2. Click **"Analizar contenido"**
3. Should see result (REAL/FAKE) within 2-3 seconds

**If works**: ✅ Content classifier works

---

## Step 3: Update Options Page (Optional)

**File**: `extension/options/options.html`

If users should be able to configure the backend URL:

### Current Options Page

The options page allows setting:
- Backend URL
- API Key
- Production mode toggle

### Testing Options

1. Right-click extension icon
2. Click **"Options"**
3. Update "Backend URL" to production URL
4. Toggle "Production mode" ON
5. Click **"Save"**
6. Test popup/sidebar again

---

## Step 4: Check Manifest Version

**File**: `extension/manifest.json`

Update version if needed (optional):

```json
{
  "version": "1.0.2",
  "description": "Detecta phishing en tiempo real (v1.0.2 - Production)"
}
```

**Changelog for 1.0.2**:
- Fixed hardcoded backend URL
- Implemented page content extraction
- Better error messages
- Health monitoring
- Production deployment support

---

## Step 5: Prepare for Chrome Store (Future)

Once tested, to publish to Chrome Web Store:

### 5.1 Create Store Assets

Required:
- 128x128 icon (exists: `extension/icons/icon128.png`)
- Screenshots (2-5, 1280x800 or similar)
- Description (240 chars max)
- Privacy policy link

### 5.2 Privacy Policy

Create `PRIVACY_POLICY.md` (if not exists):

```markdown
# Privacy Policy

## Data Collection

This extension:
- Analyzes URLs using your backend
- Sends URLs to external APIs (VirusTotal, Safe Browsing)
- Caches results locally in your browser

## Data Storage

- Extension storage: chrome.storage.local (not synced)
- Cache: URL analysis results (up to 500 entries)
- No personal data collected

## Third-Party Services

This extension uses:
- VirusTotal (https://virustotal.com)
- Google Safe Browsing (https://safebrowsing.google.com)
- Google Fact Check (https://toolbox.google.com/factcheck)

See their privacy policies for details.
```

---

## Configuration Summary

### For Development (localhost)
```javascript
Backend URL: http://localhost:8000
API Key: (empty)
Production: OFF
```

### For Production (Render)
```javascript
Backend URL: https://phishing-ia-XXXXX.onrender.com
API Key: (if configured on backend)
Production: ON
```

---

## Verification Checklist

- [ ] Extension loads without errors
- [ ] Popup shows correct backend URL in dev console
- [ ] Analyze button works on production backend
- [ ] Extract page button works
- [ ] Content analysis works
- [ ] Error messages are user-friendly
- [ ] Health check passes
- [ ] Cache is working (second request faster)
- [ ] Options page saves settings
- [ ] No console errors or warnings

---

## Rollback

If production backend has issues:

1. **Quick switch to local**:
   - Open extension options
   - Change Backend URL to `http://localhost:8000`
   - Toggle Production OFF
   - Click Save

2. **Revert code**:
   ```bash
   git checkout extension/
   ```

3. **Reload extension**:
   - Chrome: Extension settings → Reload

---

## Next Steps

After completing this task:

1. ✅ Production backend URL is set
2. ✅ Extension tested against production
3. ✅ Options page configured
4. ✅ Ready for Task 7 (OT Integration)

---

**Status**: Ready to configure ✅  
**Estimated Duration**: 30 minutes  
**Complexity**: Low (config update + testing)

