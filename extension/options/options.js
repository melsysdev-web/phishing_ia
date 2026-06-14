const DEFAULT_BACKEND = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", () => {
  const backendInput = document.getElementById("backendUrl");
  const testBtn      = document.getElementById("testBtn");
  const testStatus   = document.getElementById("testStatus");
  const saveBtn      = document.getElementById("saveBtn");
  const resetBtn     = document.getElementById("resetBtn");
  const saveFeedback = document.getElementById("saveFeedback");

  // Cargar configuración guardada
  chrome.storage.sync.get({ backendUrl: DEFAULT_BACKEND }, ({ backendUrl }) => {
    backendInput.value = backendUrl;
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
    const url = backendInput.value.trim().replace(/\/$/, "");
    if (!url) {
      setFeedback(saveFeedback, "Introduce una URL válida.", "err");
      return;
    }
    chrome.storage.sync.set({ backendUrl: url }, () => {
      setFeedback(saveFeedback, "✓ Cambios guardados", "ok");
      clearAfter(saveFeedback, 3000);
    });
  });

  // Restablecer
  resetBtn.addEventListener("click", () => {
    backendInput.value = DEFAULT_BACKEND;
    chrome.storage.sync.set({ backendUrl: DEFAULT_BACKEND }, () => {
      setFeedback(saveFeedback, "✓ Restablecido a localhost:8000", "ok");
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
