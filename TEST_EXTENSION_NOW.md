# 🧪 Test Extension Locally

**Quick start guide for testing stability improvements (commit 312c415)**

---

## Step 1: Start Backend

```powershell
cd C:\Users\Mel'S\Documents\phishing_ia
venv\Scripts\uvicorn backend.app.main:app --reload
```

Backend should be running at `http://localhost:8000`

---

## Step 2: Load Extension in Chrome

### Option A: Automated (PowerShell)
```powershell
.\load-extension.ps1
```

### Option B: Manual
1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable "Developer mode" (top right toggle)
4. Click "Load unpacked"
5. Select folder: `C:\Users\Mel'S\Documents\phishing_ia\extension`
6. Extension appears as "AI Phishing Detector"

---

## Step 3: Run Tests

### Quick Smoke Test (5 min)
1. Click extension icon → Popup opens ✅
2. Paste URL: `https://google.com` → Analyze ✅
3. Right-click extension → Open side panel → Sidebar loads ✅
4. Switch to "Contenido" tab ✅
5. Press F12, check Console → NO red errors ✅

### Full Test Suite (15 min)
See `EXTENSION_TESTING.md` for 12 comprehensive test cases:
- ✅ Popup opens
- ✅ Sidebar opens
- ✅ URL analysis
- ✅ Content analysis
- ✅ Anime.js fallback (CRITICAL)
- ✅ Missing DOM elements
- ✅ API error handling
- ✅ History feature
- ✅ Extract page content
- ✅ Input validation
- ✅ Browser compatibility

### Critical Test (2 min) - Most Important
```javascript
// Open DevTools (F12) → Console
// Paste this to simulate CDN failure:
window.anime = null;

// Close popup and reopen
// Should load without crashing, no animations
```

---

## What to Verify

### ✅ Good Signs (Extension is Stable)
- Popup loads instantly
- Sidebar loads instantly
- Analyze button works
- Results render correctly
- No crashes on any action
- Console shows NO red errors (warnings OK)
- Works even without animations

### ❌ Bad Signs (Bug Needs Fixing)
- TypeError in console
- ReferenceError in console
- Extension crashes (greyed out icon)
- Blank/empty popups
- Cannot click buttons
- Results don't appear

---

## Testing Checklist

| Component | Test | Pass? |
|-----------|------|-------|
| **Popup** | Opens without crashing | ☐ |
| **Popup** | Analyze button works | ☐ |
| **Popup** | Shows results | ☐ |
| **Sidebar** | Opens without crashing | ☐ |
| **Sidebar URL** | Analyze URL works | ☐ |
| **Sidebar Content** | Analyze text works | ☐ |
| **Backend** | Error handled gracefully | ☐ |
| **CDN Failure** | Works without anime.js | ☐ |
| **Console** | No red errors | ☐ |
| **History** | Save/load works | ☐ |

---

## Troubleshooting

### "Extension has errors"
→ Check Chrome console (F12). Click extension → should show error details.

### "No results displaying"
→ Backend not running? Check that `uvicorn` is still running.

### "Blank popup"
→ Reload extension: Go to `chrome://extensions/`, click reload button.

### "Cannot see Console errors"
→ Right-click popup → "Inspect" to open DevTools

### "Sidebar won't open"
→ Right-click extension icon → "Open side panel"

---

## Files to Review

- **`EXTENSION_TESTING.md`** — Full 12-test suite
- **`docs/EXTENSION_STABILITY.md`** — Technical details
- **`extension/popup/popup.js`** — Popup code
- **`extension/sidebar/sidebar.js`** — Sidebar code
- **`extension/services/api_client.js`** — API communication

---

## After Testing

✅ All tests passing?

→ Ready for production!

Run:
```powershell
git commit -m "test: extension stability verified locally"
git push origin main
```

---

## Questions?

See `docs/EXTENSION_STABILITY.md` for technical explanations of all the defensive code added.

---

**Time estimate**: 
- Quick smoke test: 5 minutes
- Full test suite: 15 minutes
- Total with fixes: 30 minutes

**Status**: Ready to test! 🚀
