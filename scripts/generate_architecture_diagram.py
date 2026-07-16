"""
Genera el diagrama de arquitectura del AI Phishing Detector como PNG.
Salida: docs/architecture_diagram.png
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Paleta ────────────────────────────────────────────────────────────────────
C_EXT      = "#1E3A5F"   # azul oscuro — extensión Chrome
C_API      = "#1565C0"   # azul — FastAPI
C_ORCH     = "#0277BD"   # azul medio — PhishingService
C_PARALLEL = "#00695C"   # verde — tareas paralelas
C_SEQ      = "#4527A0"   # violeta — secuencial
C_ML       = "#E65100"   # naranja — ML models
C_CACHE    = "#558B2F"   # verde oscuro — caché
C_EXT_API  = "#6A1B9A"   # morado — APIs externas
C_RISK     = "#B71C1C"   # rojo — RiskEngine
C_FUSION   = "#F57F17"   # ámbar — FusionEngine

BG         = "#F8F9FA"
BG_SECTION = "#ECEFF1"
WHITE      = "#FFFFFF"
TEXT_DARK  = "#212121"
TEXT_LIGHT = "#FFFFFF"

def box(ax, x, y, w, h, label, color, fontsize=9, text_color=TEXT_LIGHT,
        alpha=1.0, style="round,pad=0.05", sublabel=None):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=style,
        facecolor=color,
        edgecolor=WHITE,
        linewidth=1.2,
        alpha=alpha,
        zorder=3
    )
    ax.add_patch(patch)
    cy = y + h / 2 + (0.012 if sublabel else 0)
    ax.text(x + w / 2, cy, label,
            ha="center", va="center",
            fontsize=fontsize, color=text_color,
            fontweight="bold", zorder=4, wrap=False)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.018, sublabel,
                ha="center", va="center",
                fontsize=6.5, color=text_color, alpha=0.85,
                zorder=4)

def arrow(ax, x1, y1, x2, y2, color="#546E7A", lw=1.4, style="->",
          label=None, fontsize=7):
    ax.annotate("",
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle=style, color=color,
                        lw=lw, connectionstyle="arc3,rad=0.0"),
        zorder=2)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.01, my, label, fontsize=fontsize,
                color=color, ha="left", va="center", zorder=5)

def section_bg(ax, x, y, w, h, title, color, alpha=0.08):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.01",
        facecolor=color, edgecolor=color,
        linewidth=1.5, alpha=alpha, zorder=1
    )
    ax.add_patch(patch)
    ax.text(x + 0.01, y + h - 0.012, title,
            fontsize=7, color=color, fontweight="bold",
            ha="left", va="top", zorder=2, alpha=0.9)

# ── Figura ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(18, 13))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# ── Título ─────────────────────────────────────────────────────────────────────
ax.text(0.5, 0.975, "AI Phishing Detector — Arquitectura del Sistema",
        ha="center", va="top", fontsize=15, fontweight="bold",
        color=TEXT_DARK)
ax.text(0.5, 0.958, "FastAPI Backend  ·  Chrome Extension MV3  ·  ML Ensemble Pipeline",
        ha="center", va="top", fontsize=9, color="#546E7A")

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 1 — CHROME EXTENSION
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.01, 0.82, 0.98, 0.12, "CHROME EXTENSION  (Manifest V3)", C_EXT, alpha=0.12)

box(ax, 0.04, 0.845, 0.18, 0.055, "Popup",
    C_EXT, fontsize=9, sublabel="Gauge wheel · URL analysis")
box(ax, 0.26, 0.845, 0.22, 0.055, "Sidebar — Tab URL",
    C_EXT, fontsize=9, sublabel="Veredicto · ML bars · Threat Intel · Razones")
box(ax, 0.52, 0.845, 0.22, 0.055, "Sidebar — Tab Contenido",
    C_EXT, fontsize=9, sublabel="Textarea · REAL/FAKE · Confianza")
box(ax, 0.78, 0.845, 0.19, 0.055, "api_client.js",
    "#37474F", fontsize=9, sublabel="fetch() → localhost:8000")

# flechas extensión → api_client
for cx in [0.13, 0.37, 0.63]:
    arrow(ax, cx, 0.845, 0.88, 0.873, color="#90A4AE", lw=1.0)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 2 — FASTAPI ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.01, 0.715, 0.98, 0.1, "FASTAPI  (Uvicorn · Pydantic v2 · CORS)", C_API, alpha=0.10)

box(ax, 0.04,  0.735, 0.25, 0.055, "POST /predict",
    C_API, sublabel="UrlRequest (valida http/https)")
box(ax, 0.33,  0.735, 0.25, 0.055, "POST /analyze-content",
    C_API, sublabel="TextRequest → ContentClassifier")
box(ax, 0.62,  0.735, 0.16, 0.055, "GET /health",
    "#455A64", sublabel="Liveness check")
box(ax, 0.81,  0.735, 0.16, 0.055, "GET /cache/stats\nDELETE /cache",
    "#455A64", fontsize=8, sublabel="Observabilidad")

# flecha HTTP
arrow(ax, 0.875, 0.845, 0.875, 0.79, color=C_API, lw=1.5,
      label="HTTP\nlocalhost:8000", fontsize=7)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 3 — CACHE + PHISHINGSERVICE
# ══════════════════════════════════════════════════════════════════════════════
# Caché
box(ax, 0.62, 0.635, 0.36, 0.055, "URL Cache (thread-safe)",
    C_CACHE, sublabel="TTL 10 min · max 500 entradas · threading.Lock()")

# PhishingService
box(ax, 0.04, 0.635, 0.54, 0.055, "PhishingService.analyze()",
    C_ORCH, fontsize=10, sublabel="Orquestador principal · _safe() wrapping · análisis_time_ms")

# flecha /predict → service
arrow(ax, 0.165, 0.735, 0.165, 0.69, color=C_ORCH, lw=1.5)
# flecha service → cache
arrow(ax, 0.58, 0.662, 0.62, 0.662, color=C_CACHE, lw=1.2, label="hit/set", fontsize=7)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 4 — URL FEATURES (CPU)
# ══════════════════════════════════════════════════════════════════════════════
box(ax, 0.04, 0.555, 0.54, 0.048, "extract_url_features()  [CPU · instantáneo]",
    "#37474F", fontsize=8.5,
    sublabel="url_length · domain_length · path_length · num_dots · has_https · has_ip · contains_at_symbol · num_subdomains · ...")

arrow(ax, 0.31, 0.635, 0.31, 0.603, color="#546E7A", lw=1.2)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 5 — GRUPO 1: PARALELO (6 workers)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.01, 0.42, 0.98, 0.115,
           "GRUPO 1 — ThreadPoolExecutor(max_workers=6)  [tareas I/O paralelas]",
           C_PARALLEL, alpha=0.10)

tasks_g1 = [
    ("WHOIS\nget_domain_info()", "domain_age_days\nTLD · registrar", 0.02),
    ("HtmlAnalyzer\n.analyze()", "fetch HTML · BeautifulSoup\nhtml_features · page_text", 0.185),
    ("VirusTotal\nService", "70+ antivirus engines\nverdict: clean/susp/mal", 0.35),
    ("Safe Browsing\nService", "Google SB v4\nis_threat · threat_types", 0.515),
    ("Fact Check\nService", "Google FC API\nverdict: reliable/no_data", 0.68),
    ("RoBERTa\nPredictor", "distilroberta-base\nphishing_probability", 0.845),
]

bw = 0.135
for label, sub, bx in tasks_g1:
    box(ax, bx, 0.44, bw, 0.072, label, C_PARALLEL,
        fontsize=8, sublabel=sub)
    arrow(ax, bx + bw/2, 0.555, bx + bw/2, 0.512, color=C_PARALLEL, lw=1.0)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 6 — GRUPO 2 + FEATURE MAPPER
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.01, 0.305, 0.65, 0.1,
           "GRUPO 2 — depende de HtmlAnalyzer", C_ML, alpha=0.08)

box(ax, 0.04, 0.325, 0.25, 0.058, "FeatureMapper.map()",
    "#546E7A", fontsize=8.5,
    sublabel="18 features URL+HTML → RF input dict")
box(ax, 0.33, 0.325, 0.28, 0.058, "RandomForestPredictor",
    C_ML, fontsize=9,
    sublabel="random_forest_v2.pkl · feature_columns_v2.pkl\nphishing_probability")

# flechas grupo 2
arrow(ax, 0.185, 0.44, 0.165, 0.383, color=C_ML, lw=1.0)  # html → mapper
arrow(ax, 0.29, 0.354, 0.33, 0.354, color=C_ML, lw=1.0)   # mapper → RF

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 7 — FUSION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
box(ax, 0.04, 0.218, 0.56, 0.072, "FusionEngine.combine()",
    C_FUSION, fontsize=10,
    sublabel="prob = 0.40 × RandomForest  +  0.60 × RoBERTa   |   degradación elegante si un modelo falla")

# flechas hacia FusionEngine
arrow(ax, 0.47, 0.325, 0.32, 0.29, color=C_FUSION, lw=1.2)   # RF → fusion
arrow(ax, 0.9125, 0.44, 0.5, 0.29, color=C_FUSION, lw=1.2)   # RoBERTa → fusion

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 8 — RISK ENGINE
# ══════════════════════════════════════════════════════════════════════════════
box(ax, 0.04, 0.118, 0.92, 0.072, "RiskEngine.calculate()",
    C_RISK, fontsize=11,
    sublabel="score = 50 + Σ(deltas)   |   score ∈ [0, 100]   |   LOW ≥ 80  ·  MEDIUM ≥ 50  ·  HIGH < 50   |   override autoritativo si VT/SafeBrowsing confirman amenaza")

# flechas hacia RiskEngine
for sx in [0.31, 0.5]:
    arrow(ax, sx, 0.218, sx, 0.19, color=C_RISK, lw=1.0)

# señales al risk engine (anotaciones laterales)
signals = [
    (0.04, "HTTPS ±10/−20"),
    (0.16, "IP en URL −30"),
    (0.28, "@ symbol −40"),
    (0.40, "Marca ±20"),
    (0.52, "Dominio edad ±"),
    (0.64, "TLD ±"),
    (0.76, "VT −40/+10"),
    (0.88, "SB −50/+5"),
]
for sx, lbl in signals:
    ax.text(sx + 0.055, 0.108, lbl, fontsize=6, color=C_RISK,
            ha="center", va="top", alpha=0.8)

# ══════════════════════════════════════════════════════════════════════════════
# COLUMNA DERECHA — APIs EXTERNAS + MODELOS ML
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.68, 0.115, 0.31, 0.405,
           "APIs EXTERNAS  &  ML MODELS", C_EXT_API, alpha=0.08)

ext_boxes = [
    ("VirusTotal API v3",       "70+ engines · base64 URL ID",     0.72, 0.44),
    ("Google Safe Browsing v4", "is_threat · MALWARE / PHISHING",  0.72, 0.36),
    ("Google Fact Check",       "publisher_count · verdict",       0.72, 0.28),
    ("random_forest_v2.pkl",    "scikit-learn · 18 features",      0.72, 0.20),
    ("roberta_phishing/",       "distilroberta-base fine-tuned",   0.72, 0.135),
]
for lbl, sub, bx, by in ext_boxes:
    box(ax, bx, by, 0.26, 0.058, lbl, C_EXT_API, fontsize=8.5, sublabel=sub)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA 9 — SALIDA
# ══════════════════════════════════════════════════════════════════════════════
box(ax, 0.04, 0.035, 0.92, 0.052, "JSON Response",
    "#263238", fontsize=9,
    sublabel='risk_assessment · machine_learning (fusion/RF/RoBERTa) · html_analysis · url_features · domain_info · virustotal · safe_browsing · fact_check · cached · analysis_time_ms')

arrow(ax, 0.5, 0.118, 0.5, 0.087, color="#263238", lw=1.5)

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO STANDALONE (nota al margen)
# ══════════════════════════════════════════════════════════════════════════════
box(ax, 0.68, 0.035, 0.30, 0.068, "PhishingClassifier  (standalone)",
    "#37474F", fontsize=8,
    sublabel="roberta-base + cabeza custom · AdamW + warmup\nearly stopping · freeze/unfreeze layers\n[no integrado aún en PhishingService]")

# ══════════════════════════════════════════════════════════════════════════════
# LEYENDA
# ══════════════════════════════════════════════════════════════════════════════
legend_items = [
    (C_EXT,      "Chrome Extension"),
    (C_API,      "FastAPI / Endpoints"),
    (C_ORCH,     "Orquestación"),
    (C_PARALLEL, "Paralelo I/O"),
    (C_ML,       "ML (RF / Features)"),
    (C_FUSION,   "FusionEngine"),
    (C_RISK,     "RiskEngine"),
    (C_EXT_API,  "APIs ext. / Modelos"),
    (C_CACHE,    "Caché"),
]
legend_patches = [
    mpatches.Patch(facecolor=c, label=lbl, edgecolor="white")
    for c, lbl in legend_items
]
ax.legend(handles=legend_patches, loc="upper left",
          bbox_to_anchor=(0.0, 0.945),
          ncol=9, fontsize=7,
          framealpha=0.85, edgecolor="#CFD8DC",
          fancybox=True)

# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR
# ══════════════════════════════════════════════════════════════════════════════
out_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "architecture_diagram.png")

plt.tight_layout(pad=0.3)
plt.savefig(out_path, dpi=180, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close()
print(f"Diagrama guardado en: {os.path.abspath(out_path)}")
