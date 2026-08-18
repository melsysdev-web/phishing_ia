# 🎬 Extension Animation Testing Guide

**Date**: 2026-08-25  
**Version**: 1.0  
**Status**: Ready for QA

---

## Prerequisites

1. Chrome browser latest version
2. Extension loaded in developer mode
3. Open DevTools: F12 → Console tab
4. Test URLs:
   - Safe: `https://google.com`
   - Suspicious: `https://bit.ly/some-shortlink` (or any URL you want to test)

---

## Part 1: Popup Testing

### Setup
1. Click extension icon → Popup opens
2. Clear console (Ctrl+L)
3. Note: Animations use anime.js CDN

### Test 1.1: Initial Load Animation (Loading State)
**Expected**: Spinner + text fade in smoothly

1. Paste URL: `https://google.com`
2. Click "Analizar"
3. **Watch for**:
   - Spinner appears with smooth fade-in (400ms)
   - Spinner rotates smoothly (0.8s loop)
   - Text "Analizando..." fades in
   - State transitions smoothly

**✅ Pass if**: Spinner is smooth, no jank, text readable

---

### Test 1.2: Result Entry Animations
**Expected**: Gauge animates smoothly with number counter

Once analysis completes (5-15 seconds):

1. **Gauge fill animation** (1200ms):
   - Stroke-dashoffset animates from 0 to final value
   - Color matches risk level (green/yellow/red)
   - Movement is smooth (easeInOutCubic easing)

2. **Score number** (synchronized 1200ms):
   - Counter counts from 0 to final score
   - Updates in sync with gauge fill
   - Font is readable

3. **Verdict badge** (500ms delay, 500ms duration):
   - Badge appears after gauge completes
   - Scales up smoothly (0.9 → 1.0)
   - Text is centered and readable

4. **Reasons** (staggered entry, 80ms apart):
   - Each reason fades in + slides right
   - Stagger creates cascade effect
   - Hover effect: background lightens, text slides right 2px

5. **Signal pills** (staggered, 60ms apart, 300ms start):
   - Each pill scales up smoothly (0.8 → 1.0)
   - Uses back easing (bouncy feel)
   - Hover effect: translate up + shadow

**✅ Pass if**: All animations are smooth, no freezing, coordinated timing

---

### Test 1.3: State Transitions
**Expected**: Smooth fade between loading → result → error

1. **First analysis** → result appears
   - Fade-up and scale (0.95 → 1.0)
   - Duration 400ms

2. **Click retry on different URL** → transitions smoothly
   - Loading state appears with fade-in
   - Previous result fades out first

3. **Force error** (paste invalid text):
   - Error state appears with scale animation
   - Icon (⚠️) fades in
   - Error message is readable

**✅ Pass if**: No overlap, smooth transitions, no jank

---

### Test 1.4: History Animations
**Expected**: Staggered entry for history items

1. Multiple analyses build history
2. Close and reopen popup
3. History section should show:
   - Each item fades in + slides right
   - 50ms stagger between items
   - Creates waterfall effect

**✅ Pass if**: Cascade effect is visible, no items overlap

---

### Test 1.5: Responsive Behavior
1. Resize popup (inspect element, change height/width)
2. Animations should adapt:
   - Text wrapping works
   - Gauge stays centered
   - No overflow or clipping

**✅ Pass if**: Layout responsive, animations still smooth

---

## Part 2: Sidebar Testing

### Setup
1. Open any website (e.g., `google.com`)
2. Click extension icon → **Sidebar** (not popup)
3. Switch to URL tab (if on Content)
4. Open DevTools: F12 → Console

### Test 2.1: URL Analysis Animation (Sidebar)
**Expected**: Similar to popup but with extended space

1. Paste URL and click "Analizar"
2. **Loading state**:
   - Spinner + text fade in (400ms)
   - Smooth rotation

3. **Results entry** (500ms, easeOutCubic):
   - Verdict card slides down slightly + fades in (100ms delay)
   - Score bar animates (900ms cubic)
   - Number counter synchronizes (900ms)

4. **ML Models** (if available):
   - Each model row fades + slides in
   - Stagger 80ms starting at 250ms
   - Creates waterfall effect

5. **Threat Intel** (3 rows):
   - Each row staggered 80ms starting at 400ms
   - Icons (dots) change color based on status
   - Text is readable

6. **Reasons**:
   - Staggered 60ms starting at 550ms
   - Longer list than popup (no limit)
   - Hover effect: background + slight slide right

**✅ Pass if**: All sections animate in sequence, no overlap, smooth timing

---

### Test 2.2: Content Analysis Animation
**Expected**: Icon bounce + bar animation

1. Switch to "Contenido" tab
2. Paste sample text (>300 chars):
   ```
   This is a test of the emergency broadcast system. This is only a test.
   The coronavirus is a hoax created by Bill Gates to sell vaccines.
   Scientists have proven that microchips are in the vaccines.
   This information comes from trusted sources on social media.
   ```
3. Click "Analizar contenido"

4. **Loading state**:
   - Spinner fades in (400ms)
   - Text "Clasificando..." appears

5. **Result appears**:
   - Icon (✅/🚫/❓) bounces in (back easing, 600ms)
   - Label fades in + scales (100ms)
   - Bar animates width (800ms cubic, 300ms delay)
   - Percentage counter synchronizes

**✅ Pass if**: Icon has bouncy feel, bar smooth, numbers match

---

### Test 2.3: Tab Switching
**Expected**: Smooth tab transitions

1. Start analysis on URL tab (watch result appear)
2. Switch to "Contenido" tab
   - Previous results disappear (fade-out should be smooth)
   - Textarea appears without jarring
3. Switch back to URL tab
   - Results should still be there
   - Appears with same animations as before

**✅ Pass if**: No lag, smooth transitions, state preserved

---

### Test 2.4: Extract Page Button
**Expected**: Text extracted and textarea populated smoothly

1. Navigate to a real webpage (e.g., Wikipedia article)
2. Open sidebar
3. Click "📄 Usar página actual"
4. **Watch for**:
   - Button becomes disabled briefly
   - Text appears in textarea
   - Character counter updates
   - No freezing during extraction

**✅ Pass if**: Extraction smooth, no blocking, UI responsive

---

## Part 3: Performance Testing

### Test 3.1: Animation Smoothness (60 FPS)
**How to measure**:
1. Open DevTools → Performance tab
2. Start recording (Ctrl+Shift+E)
3. Analyze a URL
4. Wait for all animations to complete
5. Stop recording
6. Check FPS graph

**✅ Pass if**: FPS stays above 55-60 fps, no red bars

---

### Test 3.2: Memory Usage
**How to measure**:
1. Open DevTools → Memory tab
2. Take heap snapshot before analysis
3. Analyze URL
4. Take another snapshot after animations complete
5. Compare sizes

**✅ Pass if**: Memory increase < 2MB (anime.js is ~30KB minified)

---

### Test 3.3: Anime.js Loading
**How to verify**:
1. Open DevTools → Console
2. Type: `anime` and press Enter
3. Should show anime.js library object

**❌ Fail if**: `ReferenceError: anime is not defined`

---

## Part 4: Browser Compatibility

### Test 4.1: Chrome Stable
✅ **Target**: Latest Chrome (v120+)
- [ ] All animations smooth
- [ ] No console errors
- [ ] anime.js loads from CDN

### Test 4.2: Chrome Beta/Dev
✅ **Target**: Chrome 122+
- [ ] Same as stable
- [ ] Test with hardware acceleration on/off

---

## Troubleshooting

### Issue: Animations are jittery/janky

**Solutions**:
1. Check DevTools → Performance → FPS meter
2. Disable Chrome extensions (except this one)
3. Close other browser tabs
4. Check GPU acceleration: Settings → Advanced → GPU acceleration ON
5. Clear browser cache: Ctrl+Shift+Delete

### Issue: anime.js not loading

**Solutions**:
1. Check DevTools → Network tab
2. Look for `animejs@3.2.1/lib/anime.min.js`
3. If 404 error: CDN down, fallback needed
4. Check `popup.html` and `sidebar.html` have:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/animejs@3.2.1/lib/anime.min.js"></script>
   ```

### Issue: Animations not happening at all

**Solutions**:
1. Check DevTools Console for errors
2. Verify anime.js loaded: Type `anime` in console
3. Check if animations are commented out
4. Reload extension: chrome://extensions → Reload

### Issue: Animations lag after multiple analyses

**Solutions**:
1. Clear popup/sidebar cache
2. Restart Chrome
3. Check if history is huge (>100 items)
4. Monitor memory in DevTools

---

## Sign-Off Checklist

- [ ] Popup loading animation smooth
- [ ] Popup gauge animates correctly
- [ ] Popup reasons stagger properly
- [ ] Popup signals stagger with bounce
- [ ] Sidebar verdict card animates
- [ ] Sidebar score bar + number sync
- [ ] Sidebar ML models stagger
- [ ] Sidebar threat intel stagger
- [ ] Sidebar content result bounces
- [ ] Tab switching smooth
- [ ] No console errors
- [ ] anime.js library detected
- [ ] Performance > 55 FPS
- [ ] Memory usage reasonable
- [ ] Extract button responsive

---

## Expected Timings

### Popup Animations
| Element | Duration | Delay | Easing |
|---------|----------|-------|--------|
| Gauge fill | 1200ms | 0ms | easeInOutCubic |
| Score number | 1200ms | 0ms | easeInOutCubic |
| Verdict badge | 500ms | 100ms | easeOutBack |
| Reasons | 500ms | 200ms+ | easeOutCubic (stagger 80ms) |
| Signals | 400ms | 300ms+ | easeOutBack (stagger 60ms) |

### Sidebar Animations
| Element | Duration | Delay | Easing |
|---------|----------|-------|--------|
| Results entry | 500ms | 0ms | easeOutCubic |
| Verdict card | 500ms | 100ms | easeOutCubic |
| Score bar | 900ms | 0ms | easeInOutCubic |
| Score number | 900ms | 0ms | easeInOutCubic |
| ML models | 500ms | 250ms+ | easeOutCubic (stagger 80ms) |
| Threat intel | 500ms | 400ms+ | easeOutCubic (stagger 80ms) |
| Reasons | 500ms | 550ms+ | easeOutCubic (stagger 60ms) |
| Content icon | 600ms | 200ms | easeOutBack |
| Content bar | 800ms | 300ms | easeInOutCubic |

---

## Notes for QA

1. **First time load**: Anime.js loads from CDN (~30KB), may be slower on slow internet
2. **Subsequent loads**: Cached by browser, should be instant
3. **Stagger timing**: Creates waterfall effect, feels more natural than simultaneous animations
4. **Easing functions**:
   - `easeOutCubic`: Smooth deceleration (most common)
   - `easeInOutCubic`: Smooth acceleration + deceleration
   - `easeOutBack`: Bouncy effect (used for badges/icons)

---

**Testing Complete Confirmation**:
```
Date: ___________
Tester: ___________
Result: ✅ PASS / ❌ FAIL
Issues Found: ___________
```

---

Generated by Claude Code - Animation QA Automation
