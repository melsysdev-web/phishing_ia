# Política de privacidad — AI Phishing Detector

Última actualización: 2026-08-21

## Qué hace la extensión

AI Phishing Detector analiza, a petición explícita del usuario (no de forma automática ni en segundo plano), la URL de la pestaña activa o un texto pegado por el usuario, para estimar si corresponde a un sitio de phishing o a contenido no confiable.

## Qué datos se envían y a dónde

Cuando el usuario pulsa "Analizar" en el popup o el panel lateral:

- La **URL de la pestaña activa** (o la URL introducida manualmente) se envía al backend de AI Phishing Detector (`https://phishing-ia-smmy.onrender.com` por defecto, configurable en la página de opciones).
- El backend descarga el HTML público de esa URL para extraer características (formularios, campos ocultos, etc.) y consulta:
  - **VirusTotal** (Google/Chronicle) — reputación de la URL
  - **Google Safe Browsing** — listas de sitios maliciosos
  - **Google Fact Check Tools API** — verificación de afirmaciones
  - **WHOIS** — antigüedad y datos públicos del dominio
- En la pestaña "Análisis de contenido", el **texto que el usuario pega** se envía al backend para clasificarlo (confiable/no confiable).

No se envían credenciales, historial de navegación completo, ni datos de otras pestañas — solo la URL o el texto que el usuario elige analizar explícitamente.

## Qué se almacena

- **En tu navegador**: la URL del backend y, si la configuraste, tu API key, guardadas vía `chrome.storage.local`. Se quedan en este equipo: no se sincronizan con tu cuenta de Google ni con otros dispositivos. Ambas quedan bajo tu control desde la página de Opciones de la extensión.
- **En el backend**: los resultados de análisis se cachean en memoria hasta 10 minutos (máx. 500 entradas) solo para acelerar consultas repetidas de la misma URL, y se pierden al reiniciar el servidor. No hay base de datos ni almacenamiento permanente de URLs o textos analizados.
- **En los registros del servidor**: como cualquier servicio web, el backend registra los datos técnicos de cada petición — método, ruta, código de respuesta, tiempo de proceso y dirección IP de origen — para diagnosticar fallos y aplicar el límite de peticiones. **La URL y el texto analizados no aparecen en esos registros**, solo la ruta (`/predict`, `/analyze-content`). Los conserva el proveedor de alojamiento (Render) durante su periodo de retención y no se cruzan con ningún identificador de usuario.

## Con quién se comparten los datos

Únicamente con los servicios de terceros listados arriba (VirusTotal, Google Safe Browsing, Google Fact Check Tools, WHOIS), y solo la URL/dominio necesario para obtener su veredicto. No se venden ni se comparten datos con fines publicitarios. No hay seguimiento (tracking) ni analítica de uso del usuario más allá del registro técnico de peticiones descrito arriba.

## Permisos que solicita la extensión

| Permiso | Para qué se usa |
|---|---|
| `activeTab` | Leer la URL de la pestaña activa cuando el usuario pulsa "Analizar" |
| `scripting` | Extraer el texto visible de la página activa para la pestaña de análisis de contenido |
| `clipboardRead` | Permitir pegar una URL o texto copiado directamente en el panel |
| `storage` | Guardar la URL del backend y la API key configuradas por el usuario |
| `sidePanel` | Mostrar el panel lateral de análisis |

## Contacto

Para dudas sobre esta política o para solicitar la eliminación de datos, contactar a: melvinsantiago396@gmail.com
