const VERDICT = {
  low:    { icon: "✅", label: "SEGURO",      text: "Esta URL parece segura" },
  medium: { icon: "⚠️", label: "SOSPECHOSO",  text: "Esta URL tiene señales sospechosas" },
  high:   { icon: "🚨", label: "PELIGROSO",   text: "Esta URL es peligrosa" },
};

document.addEventListener("DOMContentLoaded", () => {

  document.getElementById("settingsBtn").addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });

  // ── Pestaña URL ───────────────────────────────────────────────────────────
  const urlInput   = document.getElementById("urlInput");
  const analyzeBtn = document.getElementById("analyzeBtn");

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
  urlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") triggerAnalyze(); });
  document.getElementById("retryBtn").addEventListener("click", triggerAnalyze);

  // ── Pestaña Contenido ─────────────────────────────────────────────────────
  const textarea          = document.getElementById("contentTextarea");
  const charCount         = document.getElementById("charCount");
  const analyzeContentBtn = document.getElementById("analyzeContentBtn");

  textarea.addEventListener("input", () => {
    charCount.textContent = textarea.value.length;
  });

  analyzeContentBtn.addEventListener("click", () =>
    analyzeContentText(textarea, analyzeContentBtn)
  );

  // ── Cambio de pestañas ────────────────────────────────────────────────────
  document.getElementById("tabUrl").addEventListener("click",     () => switchTab("url"));
  document.getElementById("tabContent").addEventListener("click", () => switchTab("content"));
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
  toggle("results",      false);
}

function showError(msg) {
  toggle("loadingState", false);
  toggle("errorState",   true);
  toggle("results",      false);
  document.getElementById("errorText").textContent = msg;
}

function toggle(id, visible) {
  document.getElementById(id).classList.toggle("hidden", !visible);
}

// ─── Render principal ─────────────────────────────────────────────────────────

function render(data) {
  const risk    = data.risk_assessment        || {};
  const vt      = data.virustotal             || {};
  const sb      = data.safe_browsing          || {};
  const fc      = data.fact_check             || {};
  const content = data.content_classification || {};
  const ml      = data.machine_learning       || {};

  const level   = (risk.risk || "HIGH").toLowerCase();
  const score   = risk.score ?? 0;
  const reasons = sortedReasons(risk.reasons || []);

  document.getElementById("results").className = `results ${level}`;

  renderVerdict(level, score);
  renderML(ml);
  renderThreatIntel(vt, sb, fc);
  renderContent(content);
  renderReasons(reasons);

  toggle("results",      true);
  toggle("loadingState", false);
  toggle("errorState",   false);

  animateScore(score);
}

// ─── Veredicto ────────────────────────────────────────────────────────────────

function renderVerdict(level, score) {
  const v    = VERDICT[level] || VERDICT.high;
  const card = document.getElementById("verdictCard");
  card.className = `verdict-card ${level}`;
  document.getElementById("verdictIcon").textContent  = v.icon;
  document.getElementById("verdictLabel").textContent = v.label;
  document.getElementById("verdictText").textContent  = v.text;
  document.getElementById("scoreBar").style.width     = `${score}%`;
}

function animateScore(target) {
  const el    = document.getElementById("scoreNum");
  const start = performance.now();
  const dur   = 600;
  function step(now) {
    const t = Math.min((now - start) / dur, 1);
    el.textContent = Math.round(t * target);
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
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
  const list = document.getElementById("reasonsList");
  list.innerHTML = "";
  if (!reasons.length) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="reason-icon">ℹ️</span> Sin señales de riesgo adicionales.`;
    list.appendChild(li);
    return;
  }
  reasons.forEach(r => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="reason-icon">${reasonIcon(r)}</span>${r}`;
    list.appendChild(li);
  });
}

// ─── Análisis de contenido manual ─────────────────────────────────────────────

async function analyzeContentText(textarea, btn) {
  const text = textarea.value.trim();
  if (text.length < 50) {
    showContentError("El texto es muy corto. Pega al menos un párrafo completo.");
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
        ? "No se pudo conectar al servidor. Verifica la URL en ⚙️ Configuración."
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
  document.getElementById("contentErrorText").textContent = msg;
}

function renderContentResult(data) {
  const label   = (data.label || "UNKNOWN").toUpperCase();
  const pctVal  = Math.round((data.confidence ?? 0) * 100);
  const isReal  = label === "REAL";
  const isFake  = label === "FAKE";
  const cls     = isReal ? "real" : isFake ? "fake" : "unknown";

  document.getElementById("contentResultIcon").textContent = isReal ? "✅" : isFake ? "🚫" : "❓";

  const labelEl = document.getElementById("contentResultLabel");
  labelEl.textContent = isReal ? "CONTENIDO REAL" : isFake ? "CONTENIDO FALSO" : "SIN DATOS";
  labelEl.className   = `content-result-label ${cls}`;

  document.getElementById("contentResultDesc").textContent =
    isReal ? "Este texto parece ser contenido legítimo."
    : isFake ? "Este texto presenta señales de desinformación."
    : "No fue posible clasificar el contenido.";

  const bar = document.getElementById("contentResultBar");
  bar.style.width = `${pctVal}%`;
  bar.className   = `content-bar-fill ${cls}`;

  const pct = document.getElementById("contentResultPct");
  pct.textContent = `${pctVal}%`;
  pct.className   = `content-pct ${cls}`;

  toggle("contentLoadingState", false);
  toggle("contentErrorState",   false);
  toggle("contentResult",       true);
}
