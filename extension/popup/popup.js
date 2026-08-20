const CIRCUM = 339.3; // 2π × r(54)

// ─── Polyfill helpers ─────────────────────────────────────────────────────────

function safeGetElement(id) {
  return document.getElementById(id) || { classList: { add: () => {}, remove: () => {}, toggle: () => {} }, textContent: '' };
}

function isAnimeAvailable() {
  return window.anime && typeof window.anime === 'function' && window.anime.timeline;
}

// ─── Historial ────────────────────────────────────────────────────────────────

const HISTORY_KEY = 'phishing_history';
const HISTORY_MAX = 10;

function saveHistory(url, data) {
  try {
    const risk = data.risk_assessment || {};
    const entry = {
      url,
      score: risk.score ?? 0,
      risk: (risk.risk || 'HIGH').toLowerCase(),
      ts: Date.now(),
    };
    let hist = loadHistory().filter(h => h.url !== url);
    hist.unshift(entry);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(hist.slice(0, HISTORY_MAX)));
  } catch (err) {
    console.error('Error guardando historial:', err);
  }
}

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function clearHistory() {
  try {
    localStorage.removeItem(HISTORY_KEY);
    safeGetElement('historySection').classList.add('hidden');
  } catch (err) {
    console.error('Error limpiando historial:', err);
  }
}

function formatTimeAgo(ts) {
  const sec = Math.floor((Date.now() - ts) / 1000);
  if (sec < 60)  return 'ahora';
  const min = Math.floor(sec / 60);
  if (min < 60)  return `${min}m`;
  const hr  = Math.floor(min / 60);
  if (hr  < 24)  return `${hr}h`;
  return `${Math.floor(hr / 24)}d`;
}

function renderHistory() {
  try {
    const hist    = loadHistory();
    const section = safeGetElement('historySection');
    const list    = safeGetElement('historyList');
    if (!hist.length) { section.classList.add('hidden'); return; }

    list.innerHTML = '';
    hist.forEach(({ url, score, risk, ts }, index) => {
      const shortUrl = url.replace(/^https?:\/\/(www\.)?/, '').slice(0, 38);
      const li = document.createElement('li');
      li.className = 'history-item';
      li.title = url;

      const dot = document.createElement('span');
      dot.className = `history-dot ${risk}`;

      const urlSpan = document.createElement('span');
      urlSpan.className = 'history-url';
      urlSpan.textContent = shortUrl;

      const scoreSpan = document.createElement('span');
      scoreSpan.className = `history-score ${risk}`;
      scoreSpan.textContent = score;

      const timeSpan = document.createElement('span');
      timeSpan.className = 'history-time';
      timeSpan.textContent = formatTimeAgo(ts);

      li.append(dot, urlSpan, scoreSpan, timeSpan);
      li.addEventListener('click', () => {
        safeGetElement('urlInput').value = url;
        analyze(url);
      });
      list.appendChild(li);

      if (isAnimeAvailable()) {
        anime.set(li, { opacity: 0, translateX: -10 });
        anime({
          targets: li,
          opacity: [0, 1],
          translateX: [-10, 0],
          duration: 400,
          delay: index * 50,
          easing: 'easeOutCubic',
        });
      } else {
        li.style.opacity = '1';
      }
    });
    section.classList.remove('hidden');
  } catch (err) {
    console.error('Error renderizando historial:', err);
  }
}

const VERDICT = {
  low:    { label: "SEGURO",      hint: "Esta URL parece segura" },
  medium: { label: "SOSPECHOSO",  hint: "Esta URL tiene señales sospechosas" },
  high:   { label: "PELIGROSO",   hint: "Esta URL es peligrosa" },
};

const POS_PATTERNS = [
  'https válido', 'limpio', 'limpia', 'legítim', 'confiable',
  'antigüedad', 'verificad', 'reconocid', 'confirman url legítima',
  'probablemente legítima', 'tld confiable', 'alta confianza',
];

function isPositive(text) {
  const lower = text.toLowerCase();
  return POS_PATTERNS.some(p => lower.includes(p));
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const clearHistoryBtn = safeGetElement("clearHistoryBtn");
    const urlInput  = safeGetElement("urlInput");
    const analyzeBtn = safeGetElement("analyzeBtn");
    const pasteBtn   = safeGetElement("pasteBtn");
    const retryBtn   = safeGetElement("retryBtn");

    if (clearHistoryBtn) clearHistoryBtn.addEventListener("click", clearHistory);

    if (urlInput && pasteBtn) {
      urlInput.addEventListener("focus", () => pasteBtn.classList.remove("hidden"));
      urlInput.addEventListener("blur",  () => {
        setTimeout(() => pasteBtn.classList.add("hidden"), 150);
      });
      urlInput.addEventListener("input", () => {
        pasteBtn.classList.toggle("hidden", urlInput.value.length > 0);
      });

      pasteBtn.addEventListener("click", async () => {
        try {
          const text = (await navigator.clipboard.readText()).trim();
          if (!text) return;
          urlInput.value = text;
          pasteBtn.classList.add("hidden");
          if (text.startsWith("http://") || text.startsWith("https://")) analyze(text);
          else urlInput.focus();
        } catch (err) {
          console.warn('Portapapeles no disponible:', err);
        }
      });
    }

    function triggerAnalyze() {
      const url = (urlInput?.value || "").trim();
      if (!url) return;
      if (!url.startsWith("http://") && !url.startsWith("https://")) {
        showError("La URL debe comenzar con http:// o https://");
        return;
      }
      analyze(url);
    }

    if (analyzeBtn) analyzeBtn.addEventListener("click", triggerAnalyze);
    if (urlInput) urlInput.addEventListener("keydown", e => { if (e.key === "Enter") triggerAnalyze(); });
    if (retryBtn) retryBtn.addEventListener("click", triggerAnalyze);

    renderHistory();

    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        const url = tabs[0]?.url || "";
        if (url.startsWith("http://") || url.startsWith("https://")) {
          if (urlInput) urlInput.value = url;
          analyze(url);
        }
      }
    } catch (err) {
      console.warn('Sin permiso de tabs:', err);
    }
  } catch (err) {
    console.error('Error en popup DOMContentLoaded:', err);
  }
});

// ─── Análisis ─────────────────────────────────────────────────────────────────

async function analyze(url) {
  const btn = document.getElementById("analyzeBtn");
  btn.disabled = true;
  showLoading();
  try {
    const data = await ApiClient.analyze(url);
    render(data);
    await setBadge(data);
    saveHistory(url, data);
    renderHistory();
  } catch (err) {
    showError(getErrorMessage(err));
  } finally {
    btn.disabled = false;
  }
}

// ─── Badge del ícono ──────────────────────────────────────────────────────────

async function setBadge(data) {
  try {
    const risk  = data.risk_assessment || {};
    const level = (risk.risk || "HIGH").toLowerCase();
    const score = risk.score ?? 0;

    const COLOR = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };

    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        const tabId = tabs[0]?.id;
        if (tabId) {
          await chrome.action.setBadgeBackgroundColor({ color: COLOR[level] || "#64748b", tabId });
          await chrome.action.setBadgeText({ text: String(score), tabId });
        }
      }
    } catch (err) {
      console.warn('No se pudo establecer badge:', err);
    }
  } catch (err) {
    console.error('Error en setBadge:', err);
  }
}

function showLoading() {
  const loadingEl = safeGetElement("loadingState");
  const errorEl = safeGetElement("errorState");
  const resultEl = safeGetElement("result");

  loadingEl.classList.remove("hidden");
  errorEl.classList.add("hidden");
  resultEl.classList.add("hidden");

  if (isAnimeAvailable()) {
    anime.set(loadingEl, { opacity: 0, scale: 0.95 });
    anime({
      targets: loadingEl,
      opacity: [0, 1],
      scale: [0.95, 1],
      duration: 400,
      easing: 'easeOutCubic',
    });
  } else {
    loadingEl.style.opacity = '1';
  }
}

function showError(msg) {
  const loadingEl = safeGetElement("loadingState");
  const errorEl = safeGetElement("errorState");
  const resultEl = safeGetElement("result");

  loadingEl.classList.add("hidden");
  errorEl.classList.remove("hidden");
  resultEl.classList.add("hidden");
  safeGetElement("errorText").textContent = msg;

  if (isAnimeAvailable()) {
    anime.set(errorEl, { opacity: 0, scale: 0.95 });
    anime({
      targets: errorEl,
      opacity: [0, 1],
      scale: [0.95, 1],
      duration: 400,
      easing: 'easeOutCubic',
    });
  } else {
    errorEl.style.opacity = '1';
  }
}

function toggle(id, visible) {
  document.getElementById(id).classList.toggle("hidden", !visible);
}

// ─── Render ───────────────────────────────────────────────────────────────────

function render(data) {
  try {
    const risk  = data.risk_assessment || {};
    const level = (risk.risk || "HIGH").toLowerCase();
    const score = risk.score ?? 0;

    const resultEl = safeGetElement("result");
    resultEl.className = `result ${level}`;

    const v = VERDICT[level] || VERDICT.high;
    safeGetElement("verdictBadge").textContent = v.label;
    safeGetElement("gaugeHint").textContent    = v.hint;

    toggle("result",       true);
    toggle("loadingState", false);
    toggle("errorState",   false);

    const fill = safeGetElement("gaugeFill");
    const gaugeNum = safeGetElement("gaugeNum");
    if (fill && fill.style) {
      fill.style.strokeDashoffset = CIRCUM;
    }

    if (isAnimeAvailable()) {
      anime.timeline()
        .add({
          targets: fill,
          strokeDashoffset: [CIRCUM, CIRCUM * (1 - score / 100)],
          duration: 1200,
          easing: 'easeInOutCubic',
        }, 0)
        .add({
          targets: gaugeNum,
          innerHTML: [0, score],
          round: 1,
          duration: 1200,
          easing: 'easeInOutCubic',
        }, 0);
    } else {
      gaugeNum.textContent = String(score);
      if (fill && fill.style) {
        fill.style.strokeDashoffset = String(CIRCUM * (1 - score / 100));
      }
    }

    renderReasons(risk.reasons || []);
    renderSignals(data);
    animateResultEntry();
  } catch (err) {
    console.error('Error en render:', err);
  }
}

function renderReasons(reasons) {
  try {
    const list = safeGetElement("reasonsList");
    if (!list) return;
    list.innerHTML = "";
    if (!Array.isArray(reasons)) return;

    reasons.slice(0, 5).forEach(text => {
      const pos = isPositive(text);
      const li  = document.createElement("li");
      li.className = "reason-item";

      const icon = document.createElement("span");
      icon.className = `reason-icon ${pos ? "pos" : "neg"}`;
      icon.textContent = pos ? "✓" : "✗";

      const label = document.createElement("span");
      label.textContent = String(text || '');

      li.append(icon, label);
      list.appendChild(li);
    });
  } catch (err) {
    console.error('Error en renderReasons:', err);
  }
}

function renderSignals(data) {
  try {
    const row = safeGetElement("signalsRow");
    if (!row) return;
    row.innerHTML = "";

    const pills = [
      _signalHTTPS(data),
      _signalVT(data),
      _signalSB(data),
      _signalML(data),
    ];

    pills.forEach(({ label, status }) => {
      const el = document.createElement("span");
      el.className = `signal-pill ${status}`;
      el.textContent = label;
      row.appendChild(el);
    });
  } catch (err) {
    console.error('Error en renderSignals:', err);
  }
}

function _signalHTTPS(data) {
  const has = data.url_features?.has_https;
  return has
    ? { label: "HTTPS ✓", status: "ok" }
    : { label: "HTTPS ✗", status: "bad" };
}

function _signalVT(data) {
  const vt = data.virustotal || {};
  if (vt.error)                  return { label: "VT —",  status: "neutral" };
  if (vt.verdict === "malicious") return { label: "VT ✗",  status: "bad" };
  if (vt.verdict === "suspicious") return { label: "VT !",  status: "warn" };
  if (vt.verdict === "clean")     return { label: "VT ✓",  status: "ok" };
  return { label: "VT —", status: "neutral" };
}

function _signalSB(data) {
  const sb = data.safe_browsing || {};
  if (sb.error)        return { label: "SB —", status: "neutral" };
  if (sb.is_threat)    return { label: "SB ✗", status: "bad" };
  return { label: "SB ✓", status: "ok" };
}

function _signalML(data) {
  const prob = data.machine_learning?.fusion?.phishing_probability;
  if (prob == null)   return { label: "ML —",  status: "neutral" };
  if (prob >= 0.65)   return { label: "ML ✗",  status: "bad" };
  if (prob >= 0.35)   return { label: "ML ~",  status: "warn" };
  return { label: "ML ✓", status: "ok" };
}

// ─── Animaciones con anime.js ─────────────────────────────────────────────────

function animateResultEntry() {
  if (!isAnimeAvailable()) {
    const resultEl = safeGetElement("result");
    if (resultEl) resultEl.style.opacity = '1';
    return;
  }

  try {
    const resultEl = safeGetElement("result");
    if (resultEl) {
      anime.set(resultEl, { opacity: 0, scale: 0.95 });
      anime({
        targets: resultEl,
        opacity: [0, 1],
        scale: [0.95, 1],
        duration: 400,
        easing: 'easeOutCubic',
      });
    }

    const reasonItems = document.querySelectorAll(".reason-item");
    if (reasonItems.length > 0) {
      anime.set(reasonItems, { opacity: 0, translateX: -10 });
      anime({
        targets: reasonItems,
        opacity: [0, 1],
        translateX: [-10, 0],
        duration: 500,
        delay: anime.stagger(80, { start: 200 }),
        easing: 'easeOutCubic',
      });
    }

    const signalPills = document.querySelectorAll(".signal-pill");
    if (signalPills.length > 0) {
      anime.set(signalPills, { opacity: 0, scale: 0.8 });
      anime({
        targets: signalPills,
        opacity: [0, 1],
        scale: [0.8, 1],
        duration: 400,
        delay: anime.stagger(60, { start: 300 }),
        easing: 'easeOutBack',
      });
    }

    const verdictBadge = document.querySelector(".verdict-badge");
    if (verdictBadge) {
      anime.set(verdictBadge, { opacity: 0, scale: 0.9 });
      anime({
        targets: verdictBadge,
        opacity: [0, 1],
        scale: [0.9, 1],
        duration: 500,
        delay: 100,
        easing: 'easeOutBack',
      });
    }
  } catch (err) {
    console.error('Error en animateResultEntry:', err);
  }
}

function animateStateChange(fromState, toState) {
  const fromEl = document.getElementById(fromState);
  const toEl = document.getElementById(toState);

  if (fromEl && !fromEl.classList.contains("hidden")) {
    anime({
      targets: fromEl,
      opacity: [1, 0],
      scale: [1, 0.95],
      duration: 300,
      easing: 'easeInCubic',
    });
  }

  if (toEl && toEl.classList.contains("hidden")) {
    anime.set(toEl, { opacity: 0, scale: 0.95 });
    anime({
      targets: toEl,
      opacity: [0, 1],
      scale: [0.95, 1],
      duration: 400,
      easing: 'easeOutCubic',
    });
  }
}

function animateHistoryEntry(historyItem) {
  anime.set(historyItem, { opacity: 0, translateX: -15, height: 0 });
  anime({
    targets: historyItem,
    opacity: [0, 1],
    translateX: [-15, 0],
    height: 'auto',
    duration: 400,
    easing: 'easeOutCubic',
  });
}
