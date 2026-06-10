const INITIAL_REASONS = 3;

const VERDICT = {
  low:    { icon: "✅", label: "SEGURO",      text: "Esta URL parece segura" },
  medium: { icon: "⚠️", label: "SOSPECHOSO",  text: "Esta URL tiene señales sospechosas" },
  high:   { icon: "🚨", label: "PELIGROSO",   text: "Esta URL es peligrosa" },
};

document.addEventListener("DOMContentLoaded", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab?.url || "";

  const urlText = document.getElementById("urlText");
  urlText.textContent = url || "Sin URL";
  urlText.title = url;

  if (!url || (!url.startsWith("http://") && !url.startsWith("https://"))) {
    showError("Esta página no tiene una URL HTTP/HTTPS analizable.");
    return;
  }

  document.getElementById("retryBtn").addEventListener("click", () => analyze(url));
  analyze(url);
});

async function analyze(url) {
  showLoading();
  try {
    const data = await ApiClient.analyze(url);
    render(data);
  } catch (err) {
    showError(
      err.message?.includes("Failed to fetch")
        ? "No se pudo conectar al servidor. ¿Está corriendo en localhost:8000?"
        : err.message || "Error desconocido."
    );
  }
}

// ─── Estados ─────────────────────────────────────────────────────────────────

function showLoading() {
  toggle("loadingState", true);
  toggle("errorState", false);
  toggle("results", false);
}

function showError(msg) {
  toggle("loadingState", false);
  toggle("errorState", true);
  toggle("results", false);
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

  const level   = (risk.risk || "HIGH").toLowerCase();
  const score   = risk.score ?? 0;
  const reasons = sortedReasons(risk.reasons || [], vt, sb);

  const resultsEl = document.getElementById("results");
  resultsEl.className = `results ${level}`;

  renderVerdict(level, score);
  renderThreatIntel(vt, sb, fc);
  renderContent(content);
  renderReasons(reasons);

  toggle("results", true);
  toggle("loadingState", false);
  toggle("errorState", false);

  animateScore(score);
}

// ─── Veredicto ────────────────────────────────────────────────────────────────

function renderVerdict(level, score) {
  const v = VERDICT[level] || VERDICT.high;

  const card = document.getElementById("verdictCard");
  card.className = `verdict-card ${level}`;

  document.getElementById("verdictIcon").textContent  = v.icon;
  document.getElementById("verdictLabel").textContent = v.label;
  document.getElementById("verdictText").textContent  = v.text;

  document.getElementById("scoreBar").style.width = `${score}%`;
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

// ─── Threat Intel ─────────────────────────────────────────────────────────────

function renderThreatIntel(vt, sb, fc) {
  setIntelRow("vt", vtStatus(vt));
  setIntelRow("sb", sbStatus(sb));
  setIntelRow("fc", fcStatus(fc));
}

function setIntelRow(prefix, { dot, text, cls }) {
  document.getElementById(`${prefix}Dot`).className    = `intel-dot ${dot}`;
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
    return { dot: "warn",   text: "Marcada como sospechosa",   cls: "warn" };

  return { dot: "safe", text: `Limpia (0 / ${total} motores)`, cls: "safe" };
}

function sbStatus(sb) {
  if (sb.error)      return { dot: "", text: "No disponible", cls: "" };
  if (!sb.is_threat) return { dot: "safe", text: "Sin amenazas detectadas", cls: "safe" };

  const types = (sb.threats || []).map((t) => friendlyThreat(t.type)).join(", ");

  if (sb.verdict === "dangerous")
    return { dot: "danger", text: types || "URL peligrosa detectada", cls: "danger" };

  return { dot: "warn", text: types || "URL sospechosa", cls: "warn" };
}

function fcStatus(fc) {
  if (!fc || fc.error) return { dot: "", text: "No disponible", cls: "" };

  const verdict = fc.verdict;
  const fake    = fc.fake_count    ?? 0;
  const pub     = fc.publisher_count ?? 0;

  if (verdict === "unreliable")
    return { dot: "danger", text: `${fake} reclamación${fake !== 1 ? "es" : ""} falsa${fake !== 1 ? "s" : ""} detectada${fake !== 1 ? "s" : ""}`, cls: "danger" };
  if (verdict === "suspicious")
    return { dot: "warn", text: "Reclamaciones cuestionadas", cls: "warn" };
  if (verdict === "reliable" && pub > 0)
    return { dot: "safe", text: "Verificador reconocido", cls: "safe" };
  if (verdict === "reliable")
    return { dot: "safe", text: "Reclamaciones verificadas", cls: "safe" };

  return { dot: "", text: "Sin datos", cls: "" };
}

// ─── Content Classification ───────────────────────────────────────────────────

function renderContent(content) {
  const label      = (content.label || "UNKNOWN").toUpperCase();
  const confidence = content.confidence ?? 0;
  const verdict    = content.verdict || "unknown";

  const badge   = document.getElementById("contentBadge");
  const bar     = document.getElementById("contentBar");
  const pct     = document.getElementById("contentPct");
  const wrap    = document.getElementById("contentBarWrap");

  const isKnown = label === "REAL" || label === "FAKE";
  const cls     = isKnown ? label.toLowerCase() : "unknown";

  badge.textContent = isKnown ? label : "SIN DATOS";
  badge.className   = `content-badge ${cls}`;

  if (isKnown) {
    const pctVal = Math.round(confidence * 100);
    bar.style.width     = `${pctVal}%`;
    bar.className       = `content-bar-fill ${cls}`;
    pct.textContent     = `${pctVal}%`;
    pct.className       = `content-pct ${cls}`;
    wrap.style.display  = "flex";
  } else {
    wrap.style.display = "none";
  }
}

function friendlyThreat(type) {
  const map = {
    MALWARE:                      "Malware",
    SOCIAL_ENGINEERING:           "Phishing / Ingeniería social",
    UNWANTED_SOFTWARE:            "Software no deseado",
    POTENTIALLY_HARMFUL_APPLICATION: "App potencialmente dañina",
  };
  return map[type] || type;
}

// ─── Razones ──────────────────────────────────────────────────────────────────

function sortedReasons(reasons, vt, sb) {
  const priority = (r) => {
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

function reasonIcon(reason) {
  const l = reason.toLowerCase();
  if (l.includes("safe browsing") || l.includes("google")) return "🛡️";
  if (l.includes("virustotal"))                             return "🔍";
  if (l.includes("fact check") || l.includes("verificador")) return "📰";
  if (l.includes("contenido") && l.includes("falso"))      return "🚫";
  if (l.includes("contenido") && l.includes("legítimo"))   return "✅";
  if (l.includes("contenido"))                             return "🧠";
  if (l.includes("https") || l.includes("http"))           return "🔓";
  if (l.includes("dominio") || l.includes("días") || l.includes("antigüedad")) return "📅";
  if (l.includes("ip"))                                     return "🌐";
  if (l.includes("palabras") || l.includes("keyword"))     return "🔑";
  if (l.includes("contraseña") || l.includes("password"))  return "🔑";
  if (l.includes("subdominio") || l.includes("redireccion")) return "🔗";
  if (l.includes("javascript"))                             return "⚙️";
  return "⚠️";
}

function renderReasons(reasons) {
  const list    = document.getElementById("reasonsList");
  const btnMore = document.getElementById("btnMore");
  list.innerHTML = "";
  btnMore.classList.add("hidden");

  if (!reasons.length) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="reason-icon">ℹ️</span> Sin señales de riesgo adicionales.`;
    list.appendChild(li);
    return;
  }

  const visible = reasons.slice(0, INITIAL_REASONS);
  const hidden  = reasons.slice(INITIAL_REASONS);

  visible.forEach((r) => list.appendChild(makeReasonLi(r)));

  if (hidden.length) {
    btnMore.textContent = `Ver ${hidden.length} razón${hidden.length > 1 ? "es" : ""} más ›`;
    btnMore.classList.remove("hidden");

    btnMore.onclick = () => {
      hidden.forEach((r) => list.appendChild(makeReasonLi(r)));
      btnMore.classList.add("hidden");
    };
  }
}

function makeReasonLi(reason) {
  const li = document.createElement("li");
  li.innerHTML = `<span class="reason-icon">${reasonIcon(reason)}</span>${reason}`;
  return li;
}
