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
 * El backend es PÚBLICO: no exige X-API-Key.
 *
 * Es una decisión, no un descuido, y por eso se declara en los dos extremos:
 * aquí con BACKEND_IS_PUBLIC y en el backend con ALLOW_UNAUTHENTICATED=true.
 * Sin esa declaración explícita el backend se niega a arrancar en producción
 * sin clave, precisamente para que una API abierta nunca sea un accidente.
 *
 * El motivo: el paquete de la tienda es descargable y descomprimible por
 * cualquiera, así que una clave embebida aquí sería pública desde el primer
 * día. Exigirla solo daría una sensación de control que no existe.
 *
 * Lo que de verdad protege el servicio es otra cosa — el límite de 30
 * peticiones/minuto por IP, el circuit breaker de cuota de VirusTotal y el
 * guardián de SSRF del fetcher de HTML.
 *
 * Si en el futuro se cierra el backend: poner la clave en BACKEND_DEFAULT_API_KEY,
 * BACKEND_IS_PUBLIC = false, API_KEY en el Environment Group de Render, quitar
 * ALLOW_UNAUTHENTICATED y publicar una versión nueva de la extensión.
 */
const BACKEND_IS_PUBLIC = true;
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
