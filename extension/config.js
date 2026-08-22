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

/**
 * Clave que la extensión envía en X-API-Key.
 *
 * NO ES UN SECRETO, y no puede serlo: el paquete de la tienda es descargable y
 * descomprimible por cualquiera, así que esta cadena es pública en cuanto se
 * publica la extensión. Ninguna credencial que viaje en un cliente puede
 * ocultarse; tratarla como secreta solo llevaría a confiar en una protección
 * que no existe.
 *
 * Para qué sirve entonces: corta el tráfico automatizado que golpea la URL del
 * backend a pelo, que es la mayoría. Lo que de verdad protege el servicio es
 * otra cosa — el límite de 30 peticiones/minuto por IP, el circuit breaker de
 * cuota de VirusTotal y el guardián de SSRF del fetcher de HTML.
 *
 * Si alguien abusa: se rota el valor en Render (Environment Group), se cambia
 * aquí y se publica una versión nueva de la extensión.
 *
 * Debe coincidir exactamente con API_KEY en el Environment Group de Render.
 * Vacía = la extensión no manda cabecera, y el backend responderá 403 a todo
 * salvo que también tenga API_KEY vacía.
 */
const BACKEND_DEFAULT_API_KEY = "";

/**
 * Timeout de las peticiones de análisis.
 *
 * 150 s y no 60 por el arranque en frío: el free tier de Render duerme el
 * servicio a los 15 minutos de inactividad y despertarlo son 60-90 s, más
 * 30-60 s de carga perezosa de los modelos en la primera petición. Con 60 s la
 * extensión abortaba justo antes de que el servidor estuviera listo, así que el
 * primer análisis tras un rato inactivo fallaba siempre.
 */
const ANALYSIS_TIMEOUT_MS = 150000;

/**
 * A partir de cuándo avisar de que el servidor estaba dormido.
 *
 * Un análisis normal tarda 2-8 s. Pasado esto es casi seguro un arranque en
 * frío, y conviene decirlo: una espera larga sin explicación se lee como que la
 * extensión está rota.
 */
const COLD_START_HINT_MS = 12000;
