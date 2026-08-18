/**
 * User-friendly error messages for common API errors.
 * Maps HTTP status codes and error types to Spanish messages.
 */

const ERROR_MESSAGES = {
  // HTTP status codes
  400: "Solicitud inválida. Verifica los datos ingresados.",
  401: "Autenticación requerida. Configura la API Key.",
  403: "Acceso denegado. Verifica los permisos.",
  404: "El servidor no está disponible.",
  429: "Demasiadas solicitudes. Espera un minuto e intenta de nuevo.",
  500: "Error en el servidor. Intenta más tarde.",
  502: "Servidor no disponible. Intenta de nuevo.",
  503: "Servidor en mantenimiento. Intenta más tarde.",

  // Special cases
  timeout: "La solicitud tomó demasiado tiempo. Intenta de nuevo.",
  offline: "Sin conexión a internet. Verifica tu conexión.",
  network: "Error de conexión. Verifica tu conexión de red.",
  unknown: "Error desconocido. Intenta de nuevo.",
};

/**
 * Get user-friendly error message from error object or status code.
 * @param {Error|number|string} error - Error object, HTTP status code, or error type
 * @returns {string} User-friendly error message in Spanish
 */
function getErrorMessage(error) {
  if (!error) return ERROR_MESSAGES.unknown;

  // If it's an AbortError (timeout)
  if (error.name === "AbortError") {
    return ERROR_MESSAGES.timeout;
  }

  // If it's a TypeError with "Failed to fetch" (network error)
  if (error instanceof TypeError && error.message.includes("Failed to fetch")) {
    return ERROR_MESSAGES.network;
  }

  // If it's a status code
  if (typeof error === "number") {
    return ERROR_MESSAGES[error] || ERROR_MESSAGES.unknown;
  }

  // If it has a status property
  if (error.status) {
    return ERROR_MESSAGES[error.status] || ERROR_MESSAGES.unknown;
  }

  // If it's a string error code
  if (typeof error === "string") {
    if (error.includes("429")) return ERROR_MESSAGES[429];
    if (error.includes("404")) return ERROR_MESSAGES[404];
    if (error.includes("500")) return ERROR_MESSAGES[500];
    if (error.includes("timeout")) return ERROR_MESSAGES.timeout;
    if (error.includes("offline")) return ERROR_MESSAGES.offline;
  }

  return ERROR_MESSAGES.unknown;
}
