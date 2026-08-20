# Local Extension Testing Guide

**Date**: 2026-08-20  
**Extension Version**: 1.0.1  
**Focus**: Test stability improvements (commit 312c415)

---

## Setup

### 1. Load Extension in Chrome

1. Open Chrome (or Edge)
2. Go to `chrome://extensions/`
3. Enable "Developer mode" (top right toggle)
4. Click "Load unpacked"
5. Select folder: `C:\Users\Mel'S\Documents\phishing_ia\extension`
6. Extension should appear as "AI Phishing Detector"

---

## Test Cases

### ✅ Test 1: Popup Opens & Loads
**Goal**: Verify popup doesn't crash on load

**Steps**:
1. Click extension icon in toolbar
2. Popup should open (not crash)
3. Should show URL input field
4. Should show "Analizar" button
5. Open DevTools (F12) → Console
6. **Should see NO errors** (only info/warnings if any)

**Expected**: ✅ Popup loads cleanly

---

### ✅ Test 2: Sidebar Opens & Loads
**Goal**: Verify sidebar doesn't crash on load

**Steps**:
1. Right-click extension icon
2. Select "Open side panel"
3. Sidebar should open (not crash)
4. Should show two tabs: "URL" and "Contenido"
5. Open DevTools (F12) → Console
6. **Should see NO errors**

**Expected**: ✅ Sidebar loads cleanly

---

### ✅ Test 3: URL Analysis (Happy Path)
**Goal**: Test normal operation with valid URL

**Prerequisites**: Backend running at `http://localhost:8000`

**Steps**:
1. Paste URL in popup: `https://google.com`
2. Click "Analizar"
3. Should show loading state
4. After ~2 seconds should show result with score
5. Should show signals (VT, SB, ML, etc.)
6. Should show reasons list
7. DevTools → No errors

**Expected**: ✅ Result renders correctly

**If fails**:
- Check backend is running: `venv\Scripts\uvicorn backend.app.main:app --reload`
- Check console error message
- Should be user-friendly Spanish error, not crash

---

### ✅ Test 4: Sidebar URL Analysis
**Goal**: Test sidebar URL panel

**Steps**:
1. Open sidebar
2. Paste URL: `https://phishing-example.com` (any URL)
3. Click "Analizar"
4. Should show loading state
5. Should show result with:
   - Verdict card (icon + label + score)
   - Score bar animation
   - ML models section
   - Threat intel rows (VT, SB, Fact Check)
   - Reasons list
6. DevTools → No errors

**Expected**: ✅ All sections render correctly

---

### ✅ Test 5: Content Analysis (Sidebar Tab 2)
**Goal**: Test content classification

**Steps**:
1. Open sidebar
2. Click "Contenido" tab
3. Paste text (at least 300 chars):
   ```
   Las vacunas contienen microchips para controlar la población. 
   Esto ha sido comprobado por expertos independientes que han 
   encontrado tecnología nanotecnológica en las inyecciones. 
   Todos deberían boicotear las vacunas inmediatamente para 
   proteger su libertad y salud. Los gobiernos nos ocultan la verdad.
   ```
4. Click "Analizar contenido"
5. Should show loading spinner
6. After ~3 seconds should show:
   - Result icon (✅ REAL or 🚫 FAKE)
   - Confidence bar
   - Result text
7. DevTools → No errors

**Expected**: ✅ Content classification works

---

### ✅ Test 6: Anime.js Fallback (Critical Test)
**Goal**: Verify extension works WITHOUT animations

**Steps**:
1. Open DevTools (F12)
2. Go to Console tab
3. Paste:
   ```javascript
   window.anime = null;
   ```
4. Close popup and reopen it
5. Popup should still load (no crash)
6. Analyze a URL
7. Result should appear **instantly** (no animations)
8. All UI elements should be visible
9. DevTools → Check for errors

**Expected**: ✅ No crash, instant rendering (no animations)

**Why this matters**: If CDN fails, extension should still work

---

### ✅ Test 7: Missing Element Fallback
**Goal**: Verify extension handles missing DOM elements

**Steps**:
1. Open DevTools (F12)
2. Go to Elements tab
3. Find `<div id="result">` in popup HTML
4. Delete it (right-click → Delete element)
5. Go back to Console tab
6. Click "Analizar" button
7. Should NOT crash
8. Should show some kind of error or blank state
9. **Should NOT have TypeError/ReferenceError in console**

**Expected**: ✅ No crash, graceful handling of missing element

---

### ✅ Test 8: API Error Handling
**Goal**: Test graceful error when backend unavailable

**Steps**:
1. Stop backend: Ctrl+C in uvicorn terminal (or close it)
2. Open popup
3. Analyze a URL
4. Should show loading state
5. After timeout should show error message in Spanish:
   - "No se pudo conectar al servidor..."
   - OR "Tiempo de espera agotado"
6. Should NOT show technical error
7. DevTools → Should show error but handled gracefully

**Expected**: ✅ Friendly error message, no crash

---

### ✅ Test 9: History Feature
**Goal**: Test history without crashing

**Steps**:
1. Analyze 3-5 different URLs
2. Should see "Recientes" section at bottom with entries
3. Click on history entry
4. Should re-analyze that URL
5. Open DevTools
6. Clear history button should work
7. Paste very long URL (>500 chars)
8. Should truncate in history display
9. DevTools → No errors

**Expected**: ✅ History works, handles edge cases

---

### ✅ Test 10: Extract Page Content (Sidebar)
**Goal**: Test content extraction from page

**Steps**:
1. Open any normal website (e.g., wikipedia.org, news.ycombinator.com)
2. Open sidebar
3. Click "Contenido" tab
4. Click "📄 Usar página actual"
5. Should show "Extrayendo..." while extracting
6. After 1-2 seconds should populate textarea with page text
7. Should NOT crash on system pages (about:, chrome://)
8. DevTools → Should show warning not error if system page

**Expected**: ✅ Extraction works on normal pages, graceful failure on system pages

---

### ✅ Test 11: Input Validation
**Goal**: Test that invalid inputs are caught

**Steps**:
1. Paste invalid URL: `not a url`
2. Click "Analizar"
3. Should show error: "La URL debe comenzar con http:// o https://"
4. Paste empty text
5. Click "Analizar contenido"
6. Should show error: "El texto es muy corto..."
7. Paste <300 char text
8. Click "Analizar contenido"
9. Should show warning about text too short

**Expected**: ✅ All validation works, friendly messages

---

### ✅ Test 12: Browser Compatibility Check
**Goal**: Quick check on different browsers

**Steps**:
1. Test in Chrome (Chromium-based) ✅
2. If available, test in Firefox (different error handling)
3. Extension should load in both
4. Functionality should be same

**Expected**: ✅ Works in both Chrome and Firefox

---

## Test Results Checklist

| Test | Result | Notes |
|------|--------|-------|
| 1. Popup opens | ✅ / ❌ | |
| 2. Sidebar opens | ✅ / ❌ | |
| 3. URL analysis | ✅ / ❌ | |
| 4. Sidebar URL tab | ✅ / ❌ | |
| 5. Content analysis | ✅ / ❌ | |
| 6. Anime.js fallback | ✅ / ❌ | **CRITICAL** |
| 7. Missing element | ✅ / ❌ | |
| 8. API error | ✅ / ❌ | |
| 9. History feature | ✅ / ❌ | |
| 10. Extract page | ✅ / ❌ | |
| 11. Input validation | ✅ / ❌ | |
| 12. Browser compat | ✅ / ❌ | |

---

## Common Issues & Solutions

### Issue: "Extension has errors"
**Solution**: Check console for specific error. If DOM-related, our `safeGetElement()` should handle it.

### Issue: "No results showing"
**Solution**: 
1. Check backend is running
2. Check console for API errors
3. Try different URL

### Issue: "Animations don't work"
**Solution**: This is normal if anime.js didn't load from CDN. UI should still work.

### Issue: "Sidebar won't open"
**Solution**:
1. Right-click extension icon again
2. Reload extension in chrome://extensions

### Issue: "History missing"
**Solution**: 
1. Check browser console for localStorage errors
2. Might be quota exceeded
3. Clear browser cache and try again

---

## Console Error Patterns (What to Watch)

### ❌ BAD (Means we have a bug)
```
TypeError: Cannot read property 'classList' of null
ReferenceError: anime is not defined
SyntaxError in JSON.parse()
```

### ✅ GOOD (Expected, handled gracefully)
```
console.warn('Portapapeles no disponible: ...')
console.error('Error guardando historial: ...')
console.warn('Sin permiso de tabs: ...')
```

---

## Performance Notes

- **Popup load time**: Should be <100ms
- **Sidebar load time**: Should be <100ms
- **URL analysis**: Should be <5s (depends on backend)
- **Content analysis**: Should be <10s (ML model runs)
- **Animations**: Should be smooth at 60fps (if anime.js loads)

---

## Final Verification

✅ All 12 tests passing?  
✅ No TypeErrors or ReferenceErrors in console?  
✅ Animations work OR graceful fallback without anime?  
✅ Extension doesn't crash on any edge case?  

**Then ready for production deployment!** 🚀

---

**Backend Requirements**:
- Python 3.12+
- `venv\Scripts\uvicorn backend.app.main:app --reload`
- Running on `http://localhost:8000`

**Extension Requirements**:
- Chrome/Edge with Manifest V3 support
- Developer mode enabled
- Loaded via "Load unpacked" (not from store)

---

**Questions?** Check `docs/EXTENSION_STABILITY.md` for detailed explanations.
