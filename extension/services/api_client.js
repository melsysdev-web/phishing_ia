const _DEFAULT_URL = "https://phishing-ia-2.onrender.com";

async function _config() {
  return new Promise(resolve => {
    chrome.storage.sync.get({ backendUrl: _DEFAULT_URL, apiKey: "" }, resolve);
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
