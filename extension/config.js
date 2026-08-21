/**
 * Configuración compartida por el popup, el sidebar, la página de opciones y
 * el service worker.
 *
 * Esta constante es la ÚNICA definición de la URL del backend. Antes cada
 * archivo llevaba la suya y las tres se desincronizaron: opciones apuntaba a
 * un host de Render que ya no existía, api_client caía en localhost y el
 * health check comprobaba un tercer sitio.
 */
const BACKEND_DEFAULT_URL = "https://phishing-ia-smmy.onrender.com";
