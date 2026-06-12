const API_BASE = "http://localhost:8000";

const ApiClient = {
  async analyze(url) {
    const response = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);
    return response.json();
  },

  async analyzeContent(text) {
    const response = await fetch(`${API_BASE}/analyze-content`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);
    return response.json();
  },
};
