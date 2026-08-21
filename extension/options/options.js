// Definida en extension/config.js, cargado antes que este script.
const DEFAULT_BACKEND = BACKEND_DEFAULT_URL;

function isLocalhost(url) {
  try {
    const { hostname, protocol } = new URL(url);
    return protocol === "https:" ||
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "::1";
  } catch {
    return true;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const backendInput = document.getElementById("backendUrl");
  const apiKeyInput  = document.getElementById("apiKey");
  const toggleKey    = document.getElementById("toggleKey");
  const testBtn      = document.getElementById("testBtn");
  const testStatus   = document.getElementById("testStatus");
  const httpWarning  = document.getElementById("httpWarning");
  const saveBtn      = document.getElementById("saveBtn");
  const resetBtn     = document.getElementById("resetBtn");
  const saveFeedback = document.getElementById("saveFeedback");

  // Cargar configuración guardada (storage.local: no se sincroniza a la
  // cuenta del navegador — la API key es una credencial, no una preferencia).
  chrome.storage.local.get({ backendUrl: DEFAULT_BACKEND, apiKey: "" }, ({ backendUrl, apiKey }) => {
    backendInput.value = backendUrl;
    apiKeyInput.value  = apiKey;
    checkHttpWarning(backendUrl);
  });

  // Advertencia HTTP
  function checkHttpWarning(url) {
    if (!isLocalhost(url)) {
      setStatus(httpWarning, "Advertencia: el backend usa HTTP sin cifrar. Usa HTTPS en producción.", "err");
    } else {
      httpWarning.textContent = "";
    }
  }
  backendInput.addEventListener("input", () => checkHttpWarning(backendInput.value.trim()));

  // Mostrar/ocultar API key
  toggleKey.addEventListener("click", () => {
    const hidden = apiKeyInput.type === "password";
    apiKeyInput.type   = hidden ? "text" : "password";
    toggleKey.textContent = hidden ? "Ocultar" : "Mostrar";
  });

  // Probar conexión
  testBtn.addEventListener("click", async () => {
    const url = backendInput.value.trim().replace(/\/$/, "");
    if (!url) {
      setStatus(testStatus, "Introduce una URL.", "err");
      return;
    }
    testBtn.disabled = true;
    setStatus(testStatus, "Probando…", "");
    try {
      const res = await fetch(`${url}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        setStatus(testStatus, "✓ Conexión exitosa", "ok");
      } else {
        setStatus(testStatus, `✗ El servidor respondió con error ${res.status}`, "err");
      }
    } catch {
      setStatus(testStatus, "✗ No se pudo conectar al servidor", "err");
    } finally {
      testBtn.disabled = false;
    }
  });

  // Guardar
  saveBtn.addEventListener("click", () => {
    const url    = backendInput.value.trim().replace(/\/$/, "");
    const apiKey = apiKeyInput.value.trim();
    if (!url) {
      setFeedback(saveFeedback, "Introduce una URL válida.", "err");
      return;
    }
    chrome.storage.local.set({ backendUrl: url, apiKey }, () => {
      setFeedback(saveFeedback, "✓ Cambios guardados", "ok");
      clearAfter(saveFeedback, 3000);
    });
  });

  // Restablecer
  resetBtn.addEventListener("click", () => {
    backendInput.value = DEFAULT_BACKEND;
    apiKeyInput.value  = "";
    checkHttpWarning(DEFAULT_BACKEND);
    chrome.storage.local.set({ backendUrl: DEFAULT_BACKEND, apiKey: "" }, () => {
      setFeedback(saveFeedback, "✓ Restablecido a valores por defecto", "ok");
      clearAfter(saveFeedback, 3000);
    });
  });
});

function setStatus(el, msg, cls) {
  el.textContent = msg;
  el.className   = `field-status ${cls}`;
}

function setFeedback(el, msg, cls) {
  el.textContent = msg;
  el.className   = `save-feedback ${cls}`;
}

function clearAfter(el, ms) {
  setTimeout(() => setFeedback(el, "", ""), ms);
}
