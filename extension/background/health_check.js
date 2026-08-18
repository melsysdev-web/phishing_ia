/**
 * Background service worker for periodic health checks.
 * Monitors backend connection status and updates extension state.
 */

// Check connection on install/update
chrome.runtime.onInstalled.addListener(async () => {
  console.log("Extension installed/updated. Running health check...");
  const connected = await testBackendConnection();
  await chrome.storage.local.set({ backendConnected: connected });
  if (!connected) {
    console.warn("Backend unreachable at startup");
  }
});

// Periodic health check every 5 minutes
chrome.alarms.create("healthCheck", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "healthCheck") {
    console.log("Running periodic health check...");
    const connected = await testBackendConnection();
    await chrome.storage.local.set({ backendConnected: connected });

    if (!connected) {
      console.warn("Backend health check failed");
    }
  }
});

/**
 * Test backend connection by calling /health endpoint.
 * @returns {boolean} True if backend is reachable, false otherwise
 */
async function testBackendConnection() {
  try {
    // Get backend URL from storage
    const config = await new Promise(resolve => {
      chrome.storage.local.get({ backendUrl: "http://localhost:8000" }, resolve);
    });

    const backendUrl = config.backendUrl || "http://localhost:8000";
    const healthUrl = backendUrl.replace(/\/$/, "") + "/health";

    // Test connection with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);  // 5s timeout

    const response = await fetch(healthUrl, {
      method: "GET",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response.ok;
  } catch (err) {
    console.error("Health check error:", err.message);
    return false;
  }
}

/**
 * Get current backend connection status (non-blocking).
 * @returns {Promise<boolean>} Whether backend is connected
 */
async function isBackendConnected() {
  const { backendConnected = false } = await chrome.storage.local.get("backendConnected");
  return backendConnected;
}
