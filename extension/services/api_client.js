const _DEFAULT_URL = "http://localhost:8000";

async function _baseUrl() {
  return new Promise(resolve => {
    chrome.storage.sync.get({ backendUrl: _DEFAULT_URL }, d => {
      resolve(d.backendUrl.replace(/\/$/, ""));
    });
  });
}

const ApiClient = {
  async analyze(url) {
    const base = await _baseUrl();
    const res = await fetch(`${base}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
    return res.json();
  },

  async analyzeContent(text) {
    const base = await _baseUrl();
    const res = await fetch(`${base}/analyze-content`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
    return res.json();
  },

  async testConnection() {
    const base = await _baseUrl();
    const res = await fetch(`${base}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`El servidor respondió con error ${res.status}`);
    return res.json();
  },
};
