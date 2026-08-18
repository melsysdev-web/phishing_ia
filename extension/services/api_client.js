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
    const res = await fetch(`${base}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ url }),
      signal: AbortSignal.timeout(60000),
    });
    if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
    return res.json();
  },

  async analyzeContent(text) {
    const { backendUrl, apiKey } = await _config();
    const base = backendUrl.replace(/\/$/, "");
    const res = await fetch(`${base}/analyze-content`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(60000),
    });
    if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
    return res.json();
  },

  async testConnection() {
    const { backendUrl } = await _config();
    const base = backendUrl.replace(/\/$/, "");
    const res = await fetch(`${base}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`El servidor respondió con error ${res.status}`);
    return res.json();
  },
};
