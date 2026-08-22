const VERDICT = {
  low:    { icon: "✅", label: "SEGURO",      text: "Esta URL parece segura" },
  medium: { icon: "⚠️", label: "SOSPECHOSO",  text: "Esta URL tiene señales sospechosas" },
  high:   { icon: "🚨", label: "PELIGROSO",   text: "Esta URL es peligrosa" },
};

function safeGetElement(id) {
  return document.getElementById(id) || { classList: { add: () => {}, remove: () => {}, toggle: () => {} }, textContent: '', innerHTML: '', style: {}, value: '' };
}

function isAnimeAvailable() {
  return window.anime && typeof window.anime === 'function' && window.anime.timeline;
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    const urlInput   = safeGetElement("urlInput");
    const analyzeBtn = safeGetElement("analyzeBtn");
    const retryBtn   = safeGetElement("retryBtn");
    const textarea   = safeGetElement("contentTextarea");
    const analyzeContentBtn = safeGetElement("analyzeContentBtn");
    const extractPageBtn = safeGetElement("extractPageBtn");
    const tabUrl = safeGetElement("tabUrl");
    const tabContent = safeGetElement("tabContent");

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
    if (urlInput) urlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") triggerAnalyze(); });
    if (retryBtn) retryBtn.addEventListener("click", triggerAnalyze);

    if (textarea) textarea.addEventListener("input", updateCharCount);
    if (extractPageBtn) extractPageBtn.addEventListener("click", extractFromActivePage);
    if (analyzeContentBtn) analyzeContentBtn.addEventListener("click", () =>
      analyzeContentText(textarea, analyzeContentBtn)
    );

    if (tabUrl) tabUrl.addEventListener("click", () => switchTab("url"));
    if (tabContent) tabContent.addEventListener("click", () => switchTab("content"));

    const feedbackSafe = safeGetElement("feedbackSafe");
    const feedbackPhishing = safeGetElement("feedbackPhishing");
    if (feedbackSafe) feedbackSafe.addEventListener("click", () => sendFeedback("LOW"));
    if (feedbackPhishing) feedbackPhishing.addEventListener("click", () => sendFeedback("HIGH"));
  } catch (err) {
    console.error('Error en sidebar DOMContentLoaded:', err);
  }
});

function switchTab(tab) {
  const isUrl = tab === "url";
  document.getElementById("panelUrl").classList.toggle("hidden", !isUrl);
  document.getElementById("panelContent").classList.toggle("hidden", isUrl);
  document.getElementById("tabUrl").classList.toggle("active", isUrl);
  document.getElementById("tabContent").classList.toggle("active", !isUrl);
}

// ─── Análisis de URL ──────────────────────────────────────────────────────────

async function analyze(url) {
  const btn = document.getElementById("analyzeBtn");
  btn.disabled = true;
  showLoading();
  try {
    const data = await ApiClient.analyze(url);
    render(data);
  } catch (err) {
    showError(getErrorMessage(err));
  } finally {
    stopColdStartHint();
    btn.disabled = false;
  }
}

// ─── Aviso de arranque en frío ────────────────────────────────────────────────
//
// El free tier de Render duerme el servicio a los 15 minutos de inactividad, y
// despertarlo son 60-90 s más la carga perezosa de los modelos. Un análisis
// normal tarda 2-8 s, así que pasado COLD_START_HINT_MS lo que hay casi seguro
// es un servidor arrancando. Decirlo importa: una espera larga sin explicación
// se lee como que la extensión no funciona, y ese es el primer contacto de
// quien acaba de instalarla.

let _coldStartTimer = null;
let _loadingSubTexto = null;

function startColdStartHint() {
  const sub = document.getElementById("loadingSub");
  if (!sub) return;
  if (_loadingSubTexto === null) _loadingSubTexto = sub.textContent;
  clearTimeout(_coldStartTimer);
  _coldStartTimer = setTimeout(() => {
    sub.textContent = "El servidor estaba en reposo; puede tardar hasta dos minutos en despertar.";
  }, COLD_START_HINT_MS);
}

function stopColdStartHint() {
  clearTimeout(_coldStartTimer);
  _coldStartTimer = null;
  const sub = document.getElementById("loadingSub");
  if (sub && _loadingSubTexto !== null) sub.textContent = _loadingSubTexto;
}

function showLoading() {
  const loadingEl = safeGetElement("loadingState");
  const errorEl = safeGetElement("errorState");
  const resultsEl = safeGetElement("results");

  loadingEl.classList.remove("hidden");
  startColdStartHint();
  errorEl.classList.add("hidden");
  resultsEl.classList.add("hidden");

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
  const resultsEl = safeGetElement("results");

  loadingEl.classList.add("hidden");
  errorEl.classList.remove("hidden");
  resultsEl.classList.add("hidden");
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

// ─── Feedback del usuario ─────────────────────────────────────────────────────

// Último análisis mostrado, para poder atribuir la corrección al veredicto
// concreto (y a la variante de scoring) que la generó.
let _lastAnalysis = null;

function renderFeedbackPrompt() {
  const section = safeGetElement("feedbackSection");
  const status = safeGetElement("feedbackStatus");
  if (!section) return;
  if (status) status.textContent = "";
  section.classList.remove("hidden");
  ["feedbackSafe", "feedbackPhishing"].forEach(id => {
    const btn = safeGetElement(id);
    if (btn) btn.disabled = false;
  });
}

async function sendFeedback(reportedRisk) {
  if (!_lastAnalysis?.url || !_lastAnalysis?.predictedRisk) return;

  const status = safeGetElement("feedbackStatus");
  const buttons = ["feedbackSafe", "feedbackPhishing"].map(safeGetElement);
  buttons.forEach(btn => { if (btn) btn.disabled = true; });
  if (status) status.textContent = "Enviando…";

  try {
    await ApiClient.submitFeedback({ ..._lastAnalysis, reportedRisk });
    if (status) status.textContent = "Gracias, tu corrección fue registrada.";
  } catch (err) {
    // El feedback es opcional: si falla, no se interrumpe el análisis mostrado.
    if (status) status.textContent = "No se pudo enviar la corrección.";
    buttons.forEach(btn => { if (btn) btn.disabled = false; });
    console.warn("Feedback no enviado:", err);
  }
}

// ─── Render principal ─────────────────────────────────────────────────────────

function render(data) {
  try {
    const risk    = data.risk_assessment        || {};
    const vt      = data.virustotal             || {};
    const sb      = data.safe_browsing          || {};
    const fc      = data.fact_check             || {};
    const content = data.content_classification || {};
    const ml      = data.machine_learning       || {};

    const level   = (risk.risk || "HIGH").toLowerCase();
    const score   = risk.score ?? 0;
    const reasons = sortedReasons(risk.reasons || []);

    safeGetElement("results").className = `results ${level}`;

    _lastAnalysis = {
      url: data.url,
      predictedRisk: risk.risk,
      predictedScore: score,
      confidence: risk.confidence,
      variant: data.scoring_variant,
    };

    renderVerdict(level, score, risk);
    renderFeedbackPrompt();
    renderML(ml);
    renderThreatIntel(vt, sb, fc);
    renderContent(content);
    renderReasons(reasons);

    toggle("results",      true);
    toggle("loadingState", false);
    toggle("errorState",   false);

    animateScore(score);
    animateResultsEntry();
  } catch (err) {
    console.error('Error en render:', err);
    showError('Error al renderizar resultados');
  }
}

// ─── Veredicto ────────────────────────────────────────────────────────────────

function renderVerdict(level, score, risk) {
  try {
    const v    = VERDICT[level] || VERDICT.high;
    const card = safeGetElement("verdictCard");
    if (card) card.className = `verdict-card ${level}`;
    safeGetElement("verdictIcon").textContent  = v.icon;
    safeGetElement("verdictLabel").textContent = v.label;
    safeGetElement("verdictText").textContent  = v.text;
    const scoreBar = safeGetElement("scoreBar");
    if (scoreBar && scoreBar.style) scoreBar.style.width = `${score}%`;
    renderConfidence(risk);
  } catch (err) {
    console.error('Error en renderVerdict:', err);
  }
}

// El backend puede omitir la calibración (respuestas cacheadas por versiones
// anteriores), en cuyo caso no se muestra nada en lugar de inventar un valor.
function renderConfidence(risk) {
  const el = safeGetElement("verdictConfidence");
  if (!el) return;
  const confidence = risk?.confidence;
  if (typeof confidence !== "number") {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }
  const pct = Math.round(confidence * 100);
  const interval = risk?.score_interval;
  const range = interval && typeof interval.lower === "number"
    ? ` · rango ${interval.lower}–${interval.upper}`
    : "";
  el.textContent = `Confianza ${pct}%${range}`;
  el.className = `verdict-confidence ${pct < 60 ? "low" : ""}`;
}

function animateScore(target) {
  if (!isAnimeAvailable()) {
    const scoreBar = safeGetElement("scoreBar");
    const scoreNum = safeGetElement("scoreNum");
    if (scoreBar && scoreBar.style) scoreBar.style.width = `${target}%`;
    if (scoreNum) scoreNum.textContent = String(target);
    return;
  }

  try {
    const scoreBar = safeGetElement("scoreBar");
    const scoreNum = safeGetElement("scoreNum");

    anime.timeline()
      .add({
        targets: scoreBar,
        width: [`0%`, `${target}%`],
        duration: 900,
        easing: 'easeInOutCubic',
      }, 0)
      .add({
        targets: scoreNum,
        innerHTML: [0, target],
        round: 1,
        duration: 900,
        easing: 'easeInOutCubic',
      }, 0);
  } catch (err) {
    console.error('Error en animateScore:', err);
  }
}

// ─── Modelos ML ───────────────────────────────────────────────────────────────

function renderML(ml) {
  const section = document.getElementById("mlSection");
  const rows    = document.getElementById("mlRows");
  rows.innerHTML = "";

  const models = [
    { name: "Fusión IA",     data: ml.fusion        || {} },
    { name: "Random Forest", data: ml.random_forest || {} },
    { name: "RoBERTa URL",   data: ml.roberta       || {} },
  ];

  let hasData = false;

  for (const { name, data } of models) {
    if (data.error !== undefined || data.phishing_probability === undefined) continue;
    hasData = true;

    const prob    = data.phishing_probability ?? 0.5;
    const pct     = Math.round(prob * 100);
    const cls     = prob >= 0.65 ? "danger" : prob >= 0.40 ? "warn" : "safe";

    const row = document.createElement("div");
    row.className = "ml-row";
    row.innerHTML = `
      <span class="ml-name">${name}</span>
      <div class="ml-bar-track">
        <div class="ml-bar-fill ${cls}" style="width:${pct}%"></div>
      </div>
      <span class="ml-pct ${cls}">${pct}%</span>
      <span class="ml-tag">phishing</span>
    `;
    rows.appendChild(row);
  }

  section.classList.toggle("hidden", !hasData);
}

// ─── Threat Intel ─────────────────────────────────────────────────────────────

function renderThreatIntel(vt, sb, fc) {
  setIntelRow("vt", vtStatus(vt));
  setIntelRow("sb", sbStatus(sb));
  setIntelRow("fc", fcStatus(fc));
}

function setIntelRow(prefix, { dot, text, cls }) {
  document.getElementById(`${prefix}Dot`).className      = `intel-dot ${dot}`;
  document.getElementById(`${prefix}Result`).textContent = text;
  document.getElementById(`${prefix}Result`).className   = `intel-result ${cls}`;
}

function vtStatus(vt) {
  if (vt.error) return { dot: "", text: "No disponible", cls: "" };
  const verdict   = vt.verdict || "clean";
  const malicious = vt.stats?.malicious ?? 0;
  const total     = vt.stats?.total_engines ?? 0;
  if (verdict === "malicious")
    return { dot: "danger", text: `${malicious} / ${total} motores detectaron amenaza`, cls: "danger" };
  if (verdict === "suspicious")
    return { dot: "warn",   text: "Marcada como sospechosa", cls: "warn" };
  return { dot: "safe", text: `Limpia (0 / ${total} motores)`, cls: "safe" };
}

function sbStatus(sb) {
  if (sb.error)      return { dot: "", text: "No disponible", cls: "" };
  if (!sb.is_threat) return { dot: "safe", text: "Sin amenazas detectadas", cls: "safe" };
  const types = (sb.threats || []).map(t => friendlyThreat(t.type)).join(", ");
  if (sb.verdict === "dangerous")
    return { dot: "danger", text: types || "URL peligrosa detectada", cls: "danger" };
  return { dot: "warn", text: types || "URL sospechosa", cls: "warn" };
}

function fcStatus(fc) {
  if (!fc || fc.error) return { dot: "", text: "No disponible", cls: "" };
  const { verdict, fake_count: fake = 0, publisher_count: pub = 0 } = fc;
  if (verdict === "unreliable")
    return { dot: "danger", text: `${fake} reclamación${fake !== 1 ? "es" : ""} falsa${fake !== 1 ? "s" : ""} detectada${fake !== 1 ? "s" : ""}`, cls: "danger" };
  if (verdict === "suspicious")
    return { dot: "warn",  text: "Reclamaciones cuestionadas", cls: "warn" };
  if (verdict === "reliable" && pub > 0)
    return { dot: "safe",  text: "Verificador reconocido", cls: "safe" };
  if (verdict === "reliable")
    return { dot: "safe",  text: "Reclamaciones verificadas", cls: "safe" };
  return { dot: "", text: "Sin datos", cls: "" };
}

function friendlyThreat(type) {
  return {
    MALWARE:                         "Malware",
    SOCIAL_ENGINEERING:              "Phishing / Ingeniería social",
    UNWANTED_SOFTWARE:               "Software no deseado",
    POTENTIALLY_HARMFUL_APPLICATION: "App potencialmente dañina",
  }[type] || type;
}

// ─── Content Classification ───────────────────────────────────────────────────

function renderContent(content) {
  const label      = (content.label || "UNKNOWN").toUpperCase();
  const confidence = content.confidence ?? 0;
  const isKnown    = label === "REAL" || label === "FAKE";
  const cls        = isKnown ? label.toLowerCase() : "unknown";

  const badge = document.getElementById("contentBadge");
  badge.textContent = isKnown ? label : "SIN DATOS";
  badge.className   = `content-badge ${cls}`;

  const wrap = document.getElementById("contentBarWrap");
  if (isKnown) {
    const pct = Math.round(confidence * 100);
    const bar = document.getElementById("contentBar");
    bar.style.width = `${pct}%`;
    bar.className   = `content-bar-fill ${cls}`;
    const pctEl = document.getElementById("contentPct");
    pctEl.textContent = `${pct}%`;
    pctEl.className   = `content-pct ${cls}`;
    wrap.style.display = "flex";
  } else {
    wrap.style.display = "none";
  }
}

// ─── Razones (sin límite en sidebar) ─────────────────────────────────────────

function sortedReasons(reasons) {
  const priority = r => {
    const l = r.toLowerCase();
    if (l.includes("safe browsing") || l.includes("google")) return 0;
    if (l.includes("virustotal"))                             return 1;
    if (l.includes("fact check"))                            return 2;
    if (l.includes("contenido"))                             return 3;
    if (l.includes("dominio creado") || l.includes("30 días")) return 4;
    return 5;
  };
  return [...reasons].sort((a, b) => priority(a) - priority(b));
}

function reasonIcon(r) {
  const l = r.toLowerCase();
  if (l.includes("safe browsing") || l.includes("google"))   return "🛡️";
  if (l.includes("virustotal"))                               return "🔍";
  if (l.includes("fact check") || l.includes("verificador")) return "📰";
  if (l.includes("contenido") && l.includes("falso"))        return "🚫";
  if (l.includes("contenido") && l.includes("legítimo"))     return "✅";
  if (l.includes("contenido"))                               return "🧠";
  if (l.includes("https") || l.includes("http"))             return "🔓";
  if (l.includes("dominio") || l.includes("días") || l.includes("antigüedad")) return "📅";
  if (l.includes("ip"))                                      return "🌐";
  if (l.includes("palabras") || l.includes("keyword"))       return "🔑";
  if (l.includes("contraseña") || l.includes("password"))    return "🔑";
  if (l.includes("subdominio") || l.includes("redireccion")) return "🔗";
  if (l.includes("javascript"))                              return "⚙️";
  return "⚠️";
}

function renderReasons(reasons) {
  try {
    const list = safeGetElement("reasonsList");
    if (!list) return;
    list.innerHTML = "";
    if (!Array.isArray(reasons) || !reasons.length) {
      const li = document.createElement("li");
      li.textContent = "ℹ️ Sin señales de riesgo adicionales.";
      list.appendChild(li);
      return;
    }
    reasons.forEach(r => {
      const li = document.createElement("li");
      const icon = document.createElement("span");
      icon.className = "reason-icon";
      icon.textContent = reasonIcon(r);
      li.append(icon, document.createTextNode(String(r || '')));
      list.appendChild(li);
    });
  } catch (err) {
    console.error('Error en renderReasons:', err);
  }
}

// ─── Extracción de texto desde la pestaña activa ──────────────────────────────

// Se serializa y ejecuta en el contexto de la página — no puede referenciar
// variables del sidebar.
function _extractPageText() {
  const selectors = ["article p", "main p", "[role='main'] p", "p"];
  for (const sel of selectors) {
    const paras = Array.from(document.querySelectorAll(sel))
      .map(p => p.innerText.trim())
      .filter(t => t.length > 30);
    const joined = paras.join(" ");
    if (joined.length >= 100) return joined.slice(0, 2000);
  }
  return (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 2000);
}

async function extractFromActivePage() {
  const btn = safeGetElement("extractPageBtn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Extrayendo...";
  }
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0 || !tabs[0]?.id) throw new Error("no-tab");
    const results = await chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: _extractPageText,
    });
    const text = results?.[0]?.result || "";
    if (!text || text.length < 50) {
      showContentError("No se pudo extraer suficiente texto de esta página.");
      return;
    }
    const textarea = safeGetElement("contentTextarea");
    if (textarea) textarea.value = text;
    updateCharCount();
  } catch (err) {
    const msg = err?.message || "";
    showContentError(
      msg.includes("Cannot access") || msg.includes("chrome://") || msg.includes("no-tab")
        ? "No se puede acceder a esta página (página del sistema o pestaña vacía)."
        : "Error al extraer el texto. Intenta pegar el texto manualmente."
    );
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "📄 Usar página actual";
    }
  }
}

// ─── Contador de caracteres con color ─────────────────────────────────────────

function updateCharCount() {
  const len       = document.getElementById("contentTextarea").value.length;
  const countEl   = document.getElementById("charCount");
  const wrapEl    = document.getElementById("charCountWrap");
  countEl.textContent = len;
  wrapEl.className = "content-char-count" + (len >= 300 ? " ok" : len > 0 ? " warn" : "");
}

// ─── Análisis de contenido manual ─────────────────────────────────────────────

async function analyzeContentText(textarea, btn) {
  const text = textarea.value.trim();
  if (text.length < 300) {
    showContentError("El texto es muy corto. Se necesitan al menos 300 caracteres para clasificar.");
    return;
  }
  showContentLoading();
  btn.disabled = true;
  try {
    const data = await ApiClient.analyzeContent(text);
    if (data.error) throw new Error(data.error);
    if (data.verdict === "no_content") {
      showContentError("El texto no tiene suficiente contenido para clasificar.");
      return;
    }
    renderContentResult(data);
  } catch (err) {
    showContentError(
      err.message?.includes("Failed to fetch")
        ? "No se pudo conectar al servidor. Intenta de nuevo en unos minutos."
        : err.message || "Error desconocido."
    );
  } finally {
    btn.disabled = false;
  }
}

function showContentLoading() {
  toggle("contentLoadingState", true);
  toggle("contentErrorState",   false);
  toggle("contentResult",       false);
}

function showContentError(msg) {
  toggle("contentLoadingState", false);
  toggle("contentErrorState",   true);
  toggle("contentResult",       false);
  safeGetElement("contentErrorText").textContent = msg;
}

function renderContentResult(data) {
  const label   = (data.label || "UNKNOWN").toUpperCase();
  const pctVal  = Math.round((data.confidence ?? 0) * 100);
  const isReal  = label === "REAL";
  const isFake  = label === "FAKE";
  const isKnown = isReal || isFake;
  const cls     = isReal ? "real" : isFake ? "fake" : "unknown";

  document.getElementById("contentResultIcon").textContent = isReal ? "✅" : isFake ? "🚫" : "❓";

  const labelEl = document.getElementById("contentResultLabel");
  labelEl.textContent = isReal ? "CONTENIDO REAL" : isFake ? "CONTENIDO FALSO" : "SIN DATOS";
  labelEl.className   = `content-result-label ${cls}`;

  document.getElementById("contentResultDesc").textContent =
    isReal ? "Este texto parece ser contenido legítimo."
    : isFake ? "Este texto presenta señales de desinformación."
    : "No fue posible clasificar el contenido.";

  toggle("contentUncertainBadge", pctVal < 60 && isKnown);
  toggle("contentLoadingState", false);
  toggle("contentErrorState",   false);
  toggle("contentResult",       true);

  // Animar con anime.js
  animateContentResult(pctVal, cls);
}

function animateContentResult(pctVal, cls) {
  const contentResult = document.getElementById("contentResult");
  const contentResultBar = document.getElementById("contentResultBar");
  const contentResultPct = document.getElementById("contentResultPct");
  const contentResultIcon = document.getElementById("contentResultIcon");

  anime.set(contentResult, { opacity: 0, scale: 0.95 });
  anime({
    targets: contentResult,
    opacity: [0, 1],
    scale: [0.95, 1],
    duration: 500,
    easing: 'easeOutCubic',
  });

  anime.set(contentResultIcon, { scale: 0 });
  anime({
    targets: contentResultIcon,
    scale: [0, 1],
    duration: 600,
    delay: 200,
    easing: 'easeOutBack',
  });

  anime.timeline()
    .add({
      targets: contentResultBar,
      width: [`0%`, `${pctVal}%`],
      duration: 800,
      delay: 300,
      easing: 'easeInOutCubic',
    }, 0)
    .add({
      targets: contentResultPct,
      innerHTML: [0, pctVal],
      round: 1,
      duration: 800,
      delay: 300,
      easing: 'easeInOutCubic',
    }, 0);
}

// ─── Animaciones con anime.js ─────────────────────────────────────────────────

function animateResultsEntry() {
  const resultsEl = document.getElementById("results");

  anime.set(resultsEl, { opacity: 0, scale: 0.98 });
  anime({
    targets: resultsEl,
    opacity: [0, 1],
    scale: [0.98, 1],
    duration: 500,
    easing: 'easeOutCubic',
  });

  // Animar verdict card
  const verdictCard = document.querySelector(".verdict-card");
  if (verdictCard) {
    anime.set(verdictCard, { opacity: 0, translateY: -10 });
    anime({
      targets: verdictCard,
      opacity: [0, 1],
      translateY: [-10, 0],
      duration: 500,
      delay: 100,
      easing: 'easeOutCubic',
    });
  }

  // Animar ML rows con stagger
  const mlRows = document.querySelectorAll(".ml-row");
  if (mlRows.length > 0) {
    anime.set(mlRows, { opacity: 0, translateX: -10 });
    anime({
      targets: mlRows,
      opacity: [0, 1],
      translateX: [-10, 0],
      duration: 500,
      delay: anime.stagger(80, { start: 250 }),
      easing: 'easeOutCubic',
    });
  }

  // Animar intel rows
  const intelRows = document.querySelectorAll(".intel-row");
  if (intelRows.length > 0) {
    anime.set(intelRows, { opacity: 0, translateX: -10 });
    anime({
      targets: intelRows,
      opacity: [0, 1],
      translateX: [-10, 0],
      duration: 500,
      delay: anime.stagger(80, { start: 400 }),
      easing: 'easeOutCubic',
    });
  }

  // Animar reasons
  const reasonItems = document.querySelectorAll(".reasons-section li");
  if (reasonItems.length > 0) {
    anime.set(reasonItems, { opacity: 0, translateX: -10 });
    anime({
      targets: reasonItems,
      opacity: [0, 1],
      translateX: [-10, 0],
      duration: 500,
      delay: anime.stagger(60, { start: 550 }),
      easing: 'easeOutCubic',
    });
  }
}
