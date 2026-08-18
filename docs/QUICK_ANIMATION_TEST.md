# ⚡ Quick Animation Verification Script

Copy-paste these commands in Chrome DevTools Console (F12) to verify animations are working.

---

## 1️⃣ Verify anime.js is Loaded

```javascript
// Check if anime.js library exists
console.log('anime.js loaded:', typeof anime !== 'undefined');
console.log('anime version:', anime.version);
```

**Expected Output**:
```
anime.js loaded: true
anime version: (version number)
```

---

## 2️⃣ Test Popup Animations

### Test Gauge Animation
Run this while popup is showing results:

```javascript
// Simulate gauge animation
const fill = document.getElementById('gaugeFill');
if (fill) {
  anime({
    targets: fill,
    strokeDashoffset: [339.3, 169.65],
    duration: 1200,
    easing: 'easeInOutCubic',
  });
  console.log('✅ Gauge animation test started (watch gauge fill right)');
} else {
  console.log('❌ gaugeFill element not found');
}
```

### Test Reason Animation
```javascript
// Animate all reason items
const reasons = document.querySelectorAll('.reason-item');
if (reasons.length > 0) {
  anime.set(reasons, { opacity: 0, translateX: -10 });
  anime({
    targets: reasons,
    opacity: [0, 1],
    translateX: [-10, 0],
    duration: 500,
    delay: anime.stagger(80),
    easing: 'easeOutCubic',
  });
  console.log(`✅ Animated ${reasons.length} reasons`);
} else {
  console.log('❌ No reason items found');
}
```

### Test Signal Pill Animation
```javascript
// Animate all signal pills
const pills = document.querySelectorAll('.signal-pill');
if (pills.length > 0) {
  anime.set(pills, { opacity: 0, scale: 0.8 });
  anime({
    targets: pills,
    opacity: [0, 1],
    scale: [0.8, 1],
    duration: 400,
    delay: anime.stagger(60, { start: 0 }),
    easing: 'easeOutBack',
  });
  console.log(`✅ Animated ${pills.length} signal pills`);
} else {
  console.log('❌ No signal pills found');
}
```

---

## 3️⃣ Test Sidebar Animations

### Test Score Bar Animation
Run this while sidebar is showing results:

```javascript
// Animate score bar
const scoreBar = document.getElementById('scoreBar');
if (scoreBar) {
  anime({
    targets: scoreBar,
    width: ['0%', '75%'],
    duration: 900,
    easing: 'easeInOutCubic',
  });
  console.log('✅ Score bar animation test started');
} else {
  console.log('❌ scoreBar element not found');
}
```

### Test ML Model Stagger
```javascript
// Animate ML model rows
const mlRows = document.querySelectorAll('.ml-row');
if (mlRows.length > 0) {
  anime.set(mlRows, { opacity: 0, translateX: -10 });
  anime({
    targets: mlRows,
    opacity: [0, 1],
    translateX: [-10, 0],
    duration: 500,
    delay: anime.stagger(80, { start: 0 }),
    easing: 'easeOutCubic',
  });
  console.log(`✅ Animated ${mlRows.length} ML models`);
} else {
  console.log('❌ No ML model rows found');
}
```

### Test Intel Row Stagger
```javascript
// Animate threat intel rows
const intelRows = document.querySelectorAll('.intel-row');
if (intelRows.length > 0) {
  anime.set(intelRows, { opacity: 0, translateX: -10 });
  anime({
    targets: intelRows,
    opacity: [0, 1],
    translateX: [-10, 0],
    duration: 500,
    delay: anime.stagger(80),
    easing: 'easeOutCubic',
  });
  console.log(`✅ Animated ${intelRows.length} threat intel rows`);
} else {
  console.log('❌ No intel rows found');
}
```

---

## 4️⃣ Test Content Result Animation

### Test Icon Bounce
```javascript
// Animate content result icon with bounce
const icon = document.getElementById('contentResultIcon');
if (icon) {
  anime.set(icon, { scale: 0 });
  anime({
    targets: icon,
    scale: [0, 1],
    duration: 600,
    easing: 'easeOutBack',
  });
  console.log('✅ Icon bounce animation test started (watch for bounce effect)');
} else {
  console.log('❌ contentResultIcon element not found');
}
```

---

## 5️⃣ Performance Check

### Monitor FPS During Animation
```javascript
// Check performance during animation
let frameCount = 0;
let lastTime = performance.now();
let fps = 0;

function measureFPS() {
  const now = performance.now();
  frameCount++;
  
  if (now >= lastTime + 1000) {
    fps = frameCount;
    console.log(`FPS: ${fps}`);
    frameCount = 0;
    lastTime = now;
  }
  
  requestAnimationFrame(measureFPS);
}

measureFPS();
console.log('📊 FPS monitoring started (target: 55-60 FPS)');
console.log('❌ Stop monitoring with: cancelAnimationFrame() or reload page');
```

---

## 6️⃣ Memory Check

### Check anime.js File Size
```javascript
// Check if anime.js is loaded from CDN
fetch('https://cdn.jsdelivr.net/npm/animejs@3.2.1/lib/anime.min.js')
  .then(r => r.blob())
  .then(blob => {
    console.log(`✅ anime.js file size: ${(blob.size / 1024).toFixed(1)} KB`);
  })
  .catch(e => console.error('❌ Failed to load anime.js from CDN:', e));
```

---

## 7️⃣ Comprehensive Health Check

Run this complete check:

```javascript
console.log('=== Animation System Health Check ===\n');

// 1. Check anime.js
const animeLoaded = typeof anime !== 'undefined';
console.log(`1. anime.js: ${animeLoaded ? '✅' : '❌'}`);

// 2. Check popup elements
const popupElements = {
  gaugeFill: !!document.getElementById('gaugeFill'),
  reasonsList: !!document.getElementById('reasonsList'),
  signalsRow: !!document.getElementById('signalsRow'),
};
console.log(`2. Popup elements: ${Object.values(popupElements).filter(Boolean).length}/3`);

// 3. Check sidebar elements
const sidebarElements = {
  scoreBar: !!document.getElementById('scoreBar'),
  mlRows: !!document.querySelectorAll('.ml-row').length,
  intelRows: !!document.querySelectorAll('.intel-row').length,
};
console.log(`3. Sidebar elements: ${Object.values(sidebarElements).filter(Boolean).length}/3`);

// 4. Check CSS will-change
const resultsEl = document.getElementById('result') || document.getElementById('results');
if (resultsEl) {
  const willChange = window.getComputedStyle(resultsEl).willChange;
  console.log(`4. CSS will-change: ${willChange !== 'auto' ? '✅' : '❌'} (${willChange})`);
}

// 5. Check for console errors
console.log(`\n5. Check console above for any errors (should be none)`);
console.log('\n=== Check Complete ===');
```

**Expected Output**:
```
=== Animation System Health Check ===

1. anime.js: ✅
2. Popup elements: 3/3
3. Sidebar elements: 3/3
4. CSS will-change: ✅ (opacity, transform)

5. Check console above for any errors (should be none)

=== Check Complete ===
```

---

## 🔧 Debugging Tips

### If animations don't appear:

1. **Check DevTools Console** - Look for red error messages
2. **Reload extension**:
   - chrome://extensions
   - Find this extension
   - Click "Reload" button
3. **Check anime.js loads**:
   - DevTools → Network tab
   - Filter for "anime"
   - Should see `anime.min.js` with 200 status

### If animations are slow/janky:

1. **Close other Chrome tabs** - They consume resources
2. **Disable other extensions** - Settings → Extensions → Disable all
3. **Check GPU acceleration**: Settings → Advanced → GPU acceleration → ON
4. **Run FPS monitor** - See performance check above

### If you see errors like `anime is not defined`:

1. anime.js failed to load from CDN
2. Check internet connection
3. Try CDN alternative: Update URLs in HTML files to use different CDN

---

## 📝 Test Results Template

Copy this and fill out:

```
Date: ___________
Browser: Chrome Version ___________

Popup Tests:
- [ ] Gauge animation smooth
- [ ] Reason stagger working
- [ ] Signal pills bounce
- [ ] History cascade animation
- [ ] No console errors

Sidebar Tests:
- [ ] Score bar animates
- [ ] ML models stagger
- [ ] Threat intel stagger
- [ ] Content icon bounces
- [ ] No console errors

Performance:
- FPS: _________ (target 55-60)
- Memory increase: _________ KB

Overall: ✅ PASS / ❌ FAIL

Issues found:
_____________________________
_____________________________
```

---

**Note**: These tests assume the extension popup/sidebar is open and showing results. Analyze a URL first, then run these commands.
