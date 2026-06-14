const CIRCUM = 339.3; // 2π × r(54)

const VERDICT = {
  low:    { label: "SEGURO",      hint: "Esta URL parece segura" },
  medium: { label: "SOSPECHOSO",  hint: "Esta URL tiene señales sospechosas" },
  high:   { label: "PELIGROSO",   hint: "Esta URL es peligrosa" },
};

document.addEventListener("DOMContentLoaded", () => {

  document.getElementById("settingsBtn").addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });

  const urlInput   = document.getElementById("urlInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const pasteBtn   = document.getElementById("pasteBtn");

  // ── Botón pegar ───────────────────────────────────────────────────────────
  urlInput.addEventListener("focus", () => pasteBtn.classList.remove("hidden"));

  urlInput.addEventListener("blur", () => {
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
      if (text.startsWith("http://") || text.startsWith("https://")) {
        analyze(text);
      } else {
        urlInput.focus();
      }
    } catch { /* portapapeles no disponible */ }
  });

  // ── Analizar ──────────────────────────────────────────────────────────────
  function triggerAnalyze() {
    const url = urlInput.value.trim();
    if (!url) return;
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      showError("La URL debe comenzar con http:// o https://");
      return;
    }
    analyze(url);
  }

  analyzeBtn.addEventListener("click", triggerAnalyze);
  urlInput.addEventListener("keydown", e => { if (e.key === "Enter") triggerAnalyze(); });
  document.getElementById("retryBtn").addEventListener("click", triggerAnalyze);
});

// ─── Análisis ────────────────────────────────────────────────────────────────

async function analyze(url) {
  const btn = document.getElementById("analyzeBtn");
  btn.disabled = true;
  showLoading();
  try {
    const data = await ApiClient.analyze(url);
    render(data);
  } catch (err) {
    showError(
      err.message?.includes("Failed to fetch")
        ? "No se pudo conectar al servidor. Verifica la URL en ⚙️ Configuración."
        : err.message || "Error desconocido."
    );
  } finally {
    btn.disabled = false;
  }
}

function showLoading() {
  toggle("loadingState", true);
  toggle("errorState",   false);
  toggle("result",       false);
}

function showError(msg) {
  toggle("loadingState", false);
  toggle("errorState",   true);
  toggle("result",       false);
  document.getElementById("errorText").textContent = msg;
}

function toggle(id, visible) {
  document.getElementById(id).classList.toggle("hidden", !visible);
}

// ─── Render ───────────────────────────────────────────────────────────────────

function render(data) {
  const risk  = data.risk_assessment || {};
  const level = (risk.risk || "HIGH").toLowerCase();
  const score = risk.score ?? 0;

  const resultEl = document.getElementById("result");
  resultEl.className = `result ${level}`;

  const v = VERDICT[level] || VERDICT.high;
  document.getElementById("gaugeVerdict").textContent = v.label;
  document.getElementById("gaugeHint").textContent    = v.hint;

  // ── Animar rueda ──────────────────────────────────────────────────────────
  const fill = document.getElementById("gaugeFill");
  fill.style.strokeDashoffset = CIRCUM; // reset a vacío
  // Doble rAF para que el browser pinte el reset antes de la transición
  requestAnimationFrame(() => requestAnimationFrame(() => {
    fill.style.strokeDashoffset = CIRCUM * (1 - score / 100);
  }));

  animateNumber("gaugeNum", score);

  toggle("result",       true);
  toggle("loadingState", false);
  toggle("errorState",   false);
}

function animateNumber(id, target) {
  const el    = document.getElementById(id);
  const start = performance.now();
  const dur   = 750;
  (function step(now) {
    const t = Math.min((now - start) / dur, 1);
    const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
    el.textContent = Math.round(ease * target);
    if (t < 1) requestAnimationFrame(step);
  })(performance.now());
}

