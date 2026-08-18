# 🎨 Animation Reference Guide

Complete reference of all animations in popup and sidebar.

---

## Popup Animations

### 1. Loading State

```
Timeline:
0ms  ├─ Spinner appears (fade-in, 400ms)
     └─ Text fades in (400ms)
0-750ms → Spinner rotates (0.8s loop)
```

**Code**:
```javascript
anime.set(loadingEl, { opacity: 0, scale: 0.95 });
anime({
  targets: loadingEl,
  opacity: [0, 1],
  scale: [0.95, 1],
  duration: 400,
  easing: 'easeOutCubic',
});
```

---

### 2. Gauge Fill Animation

```
Gauge Fill (1200ms):
  0%    ├─ Stroke-dashoffset: 339.3 (empty)
        └─ Scale: 0.95 → 1.0
  100%  └─ Stroke-dashoffset: 169.65 (50% filled, example)

Score Number (synchronized):
  0-1200ms → Number counter: 0 → score
```

**Easing Curve**:
```
easeInOutCubic:
  ╱╲
 ╱  ╲
╱    ╲  (smooth acceleration + deceleration)
```

**HTML**:
```html
<svg class="gauge-svg" viewBox="0 0 140 140">
  <circle class="gauge-track" cx="70" cy="70" r="54"/>
  <circle class="gauge-fill" id="gaugeFill"
    cx="70" cy="70" r="54"
    transform="rotate(-90 70 70)"/>
  <text class="gauge-num" id="gaugeNum" x="70" y="67">0</text>
</svg>
```

---

### 3. Verdict Badge Animation

```
Verdict Badge (500ms delay, 500ms duration):
  0ms   └─ Hidden (opacity: 0, scale: 0.9)
  100ms ├─ Start animation
  600ms └─ Visible (opacity: 1, scale: 1.0)

Easing: easeOutBack (bouncy)
```

**Visual**:
```
Scale timeline with easeOutBack:
        ╱╲╲
       ╱   ╲╲
      ╱     ╲  (bounces slightly)
1.0 ╱───────╲
    ╲       ╱
     ╲     ╱
0.9  ╲───╱
```

---

### 4. Reasons List Stagger

```
Reason Items (5 items example):
  
  Item 1: ├─ 0ms (delay)   → 200ms (start) → 700ms (complete)
  Item 2: ├─ 80ms (delay)  → 280ms (start) → 780ms (complete)
  Item 3: ├─ 160ms (delay) → 360ms (start) → 860ms (complete)
  Item 4: ├─ 240ms (delay) → 440ms (start) → 940ms (complete)
  Item 5: └─ 320ms (delay) → 520ms (start) → 1020ms (complete)
  
  Stagger: 80ms between each item
  Total duration: 500ms per item
```

**Animation per item**:
```javascript
{
  opacity: [0, 1],
  translateX: [-10, 0],
  duration: 500,
  delay: anime.stagger(80, { start: 200 }),
  easing: 'easeOutCubic',
}
```

**Visual cascade**:
```
Time ──────────────────────────
Item1 ===
Item2   ===
Item3     ===
Item4       ===
Item5         ===
```

---

### 5. Signal Pills Stagger + Bounce

```
Signal Pills (4 pills example):
  
  Pill 1: ├─ 0ms (delay)   → 300ms (start) → 700ms (complete)
  Pill 2: ├─ 60ms (delay)  → 360ms (start) → 760ms (complete)
  Pill 3: ├─ 120ms (delay) → 420ms (start) → 820ms (complete)
  Pill 4: └─ 180ms (delay) → 480ms (start) → 880ms (complete)
  
  Stagger: 60ms between items
  Easing: easeOutBack (bouncy)
```

**Easing Curve - easeOutBack**:
```
Scale timeline:
1.05 ╱╲  (overshoots slightly, bouncy)
1.00 ╱──╲
0.80   ╲
```

---

## Sidebar Animations

### 1. Results Entry

```
Results Container (500ms):
  0-500ms → Fade in + scale up (0.98 → 1.0)
  Easing: easeOutCubic
```

---

### 2. Verdict Card

```
Verdict Card (500ms duration, 100ms delay):
  0ms   └─ Hidden (opacity: 0, translateY: -10px)
  100ms ├─ Start animation
  600ms └─ Visible (opacity: 1, translateY: 0px)
  
  Easing: easeOutCubic
```

---

### 3. Score Bar & Number (Synchronized)

```
Score Bar Animation (900ms):
  0-900ms → width: 0% → target% (e.g., 75%)
  Easing: easeInOutCubic

Score Number Animation (synchronized, 900ms):
  0-900ms → innerHTML: 0 → target (e.g., 75)
  Easing: easeInOutCubic
```

**Timeline**:
```
Bar:    0% ─────────────────────────────── 75%
        │←─────── 900ms ─────────→│
Number: 0  ─────────────────────────────── 75
        │←─────── 900ms ─────────→│
```

---

### 4. ML Models Stagger

```
ML Rows (3 models example):
  
  Fusión IA:      ├─ 250ms (start)  → 750ms (complete)
  Random Forest:  ├─ 330ms (start)  → 830ms (complete)
  RoBERTa URL:    └─ 410ms (start)  → 910ms (complete)
  
  Stagger: 80ms between items
  Start delay: 250ms
  Duration per item: 500ms
```

---

### 5. Threat Intel Stagger

```
Intel Rows (3 services: VT, SB, Fact Check):
  
  VirusTotal:     ├─ 400ms (start)  → 900ms (complete)
  Safe Browsing:  ├─ 480ms (start)  → 980ms (complete)
  Fact Check:     └─ 560ms (start)  → 1060ms (complete)
  
  Stagger: 80ms between items
  Start delay: 400ms
```

---

### 6. Reasons Stagger

```
Reason Items (n items):
  
  Item 1: ├─ 550ms (start) → 1050ms (complete)
  Item 2: ├─ 610ms (start) → 1110ms (complete)
  Item 3: ├─ 670ms (start) → 1170ms (complete)
  ...
  
  Stagger: 60ms between items
  Start delay: 550ms
```

---

### 7. Content Result Icon Bounce

```
Content Result Icon (600ms duration, 200ms delay):
  0ms   └─ Hidden (scale: 0)
  200ms ├─ Start animation
  800ms └─ Visible (scale: 1.0, with bounce overshoot)
  
  Easing: easeOutBack (bouncy)
```

**Scale animation with easeOutBack**:
```
scale
1.1   ╱╲╲
1.0  ╱───╲╲  (bounces and settles)
      │    ╲╲
      │     ╲
0.0   └──────╲
      200ms 800ms
```

---

### 8. Content Result Bar Animation

```
Content Bar (800ms duration, 300ms delay):
  0ms   └─ Hidden (width: 0%)
  300ms ├─ Start animation
  1100ms └─ Visible (width: target%, e.g., 85%)
  
  Easing: easeInOutCubic
```

---

## Animation Timings Summary

### Quick Reference Table

| Component | Duration | Start Delay | Stagger | Easing |
|-----------|----------|-------------|---------|--------|
| **Popup** | | | | |
| Loading state | 400ms | 0ms | — | easeOutCubic |
| Gauge fill | 1200ms | 0ms | — | easeInOutCubic |
| Score number | 1200ms | 0ms | — | easeInOutCubic |
| Verdict badge | 500ms | 100ms | — | easeOutBack |
| Reasons | 500ms | 200ms | 80ms | easeOutCubic |
| Signals | 400ms | 300ms | 60ms | easeOutBack |
| History items | 400ms | 0ms | 50ms | easeOutCubic |
| **Sidebar** | | | | |
| Results entry | 500ms | 0ms | — | easeOutCubic |
| Verdict card | 500ms | 100ms | — | easeOutCubic |
| Score bar | 900ms | 0ms | — | easeInOutCubic |
| Score number | 900ms | 0ms | — | easeInOutCubic |
| ML models | 500ms | 250ms | 80ms | easeOutCubic |
| Threat intel | 500ms | 400ms | 80ms | easeOutCubic |
| Reasons | 500ms | 550ms | 60ms | easeOutCubic |
| Content icon | 600ms | 200ms | — | easeOutBack |
| Content bar | 800ms | 300ms | — | easeInOutCubic |

---

## Easing Functions Used

### easeOutCubic
**Formula**: `1 - (1 - t)³`
- Smooth deceleration
- Used for most fade/slide animations
- Feels natural and responsive

**Curve**:
```
╱─╲  (fast start, slow end)
```

### easeInOutCubic
**Formula**: `t < 0.5 ? 4t³ : 1 - (-2t + 2)³/2`
- Smooth acceleration + deceleration
- Used for progress bars and counters
- Feels methodical and measured

**Curve**:
```
  ╱╲  (slow, fast, slow)
```

### easeOutBack
**Formula**: Custom cubic Bézier
- Bouncy overshoot effect
- Used for badges and icons
- Feels playful and energetic

**Curve**:
```
╱╲╲  (bounces past target, settles)
```

---

## Performance Considerations

### will-change Hints
```css
/* Applied to animated elements */
will-change: opacity, transform;
will-change: width;
will-change: contents; /* for number counters */
```

### GPU Acceleration
- Transforms (translateX, scale) use GPU ✅
- Opacity changes use GPU ✅
- Width changes use CPU (but only progress bars)
- Color changes use CPU (but only dots)

### Recommended Settings
- Chrome GPU acceleration: **ON**
- Hardware acceleration: **ON**
- Reduced motion: **OFF** (respects user preference)

---

## Responsive Behavior

### Popup (340px width)
- Gauge: 140px fixed, centered
- Text: wraps gracefully
- Animations: same duration/easing

### Sidebar (variable width, typically 360px-600px)
- Verdict card: scales with width
- Bars: expand/contract with width
- Animations: same duration/easing

---

## Accessibility Notes

### Respects prefers-reduced-motion
```css
@media (prefers-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Note**: Currently not implemented. Consider adding for better accessibility.

---

## Testing Checklist

- [ ] All animations smooth (no jank)
- [ ] Timing synced correctly
- [ ] Stagger creates waterfall effect
- [ ] Easing feels natural
- [ ] FPS > 55 during animations
- [ ] Memory stable after animation complete
- [ ] No visual overflow/clipping
- [ ] Works on different screen sizes
- [ ] No console errors

---

**Last Updated**: 2026-08-25  
**Library**: anime.js v3.2.1  
**Browser**: Chrome 120+
