// Default backend URL — can be overridden in options
const _DEFAULT_URL = "http://localhost:8000";
const _PRODUCTION_URL = "https://phishing-ia.onrender.com";

async function _config() {
  return new Promise(resolve => {
    // storage.local, no .sync — evita que la API key viaje a la nube de la
    // cuenta del navegador junto con las demás preferencias sincronizadas.
    chrome.storage.local.get({
      backendUrl: _DEFAULT_URL,
      apiKey: "",
      production: false,  // Whether to use production URL
    }, (config) => {
      // If production mode is enabled, use production URL (unless URL is custom)
      if (config.production && config.backendUrl === _DEFAULT_URL) {
        config.backendUrl = _PRODUCTION_URL;
      }
      resolve(config);
    });
  });
}

const ApiClient = {
  async analyze(url) {
    const { backendUrl, apiKey } = await _config();
    const base = backendUrl.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ url }),
        signal: AbortSignal.timeout(60000),
      });
      if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
      const data = await res.json();
      if (!data || typeof data !== 'object') {
        throw new Error('Respuesta inválida del servidor');
      }
      return data;
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('Tiempo de espera agotado');
      }
      throw err;
    }
  },

  async analyzeContent(text) {
    const { backendUrl, apiKey } = await _config();
    const base = backendUrl.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/analyze-content`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ text }),
        signal: AbortSignal.timeout(60000),
      });
      if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
      const data = await res.json();
      if (!data || typeof data !== 'object') {
        throw new Error('Respuesta inválida del servidor');
      }
      return data;
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('Tiempo de espera agotado');
      }
      throw err;
    }
  },

  // Reporta que un veredicto fue incorrecto. La URL viaja para que el backend
  // la hashee; nunca se persiste en claro.
  async submitFeedback({ url, predictedRisk, predictedScore, reportedRisk, confidence, variant }) {
    const { backendUrl, apiKey } = await _config();
    const base = backendUrl.replace(/\/$/, "");
    const body = {
      url,
      predicted_risk: predictedRisk,
      predicted_score: predictedScore,
      reported_risk: reportedRisk,
    };
    if (typeof confidence === "number") body.confidence = confidence;
    if (variant) body.variant = variant;

    try {
      const res = await fetch(`${base}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(10000),
      });
      if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
      return res.json();
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('Tiempo de espera agotado');
      }
      throw err;
    }
  },

  async testConnection() {
    const { backendUrl } = await _config();
    const base = backendUrl.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) throw new Error(`El servidor respondió con error ${res.status}`);
      return res.json();
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('Tiempo de espera agotado');
      }
      throw err;
    }
  },
};
