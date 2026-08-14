# Ficha para Microsoft Edge Add-ons — AI Phishing Detector

Borrador de los textos del formulario de Partner Center (https://partner.microsoft.com/dashboard/microsoftedge). Ajustar antes de enviar si algo no aplica.

Fuente: [Publish a Microsoft Edge extension](https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/publish/publish-extension) y [Register as a Microsoft Edge extension developer](https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/publish/create-dev-account) (Microsoft Learn).

## Cuenta de desarrollador

- Sin cuota de registro (a diferencia de Chrome Web Store).
- Requiere una cuenta Microsoft (MSA) — Outlook/Live/Hotmail, o puedes crear una a partir de tu cuenta de GitHub.
- Registro en https://partner.microsoft.com/dashboard/microsoftedge/public/login → cuenta tipo **Individual** (más rápida de verificar que la de empresa).

## Descripción corta (short description, del manifest o del formulario)

Analiza la URL o el contenido de la página actual con IA y threat intelligence para detectar phishing en tiempo real.

## Descripción larga (mínimo 250, máximo 10.000 caracteres)

AI Phishing Detector analiza, bajo tu control (nunca en segundo plano), la URL de la página que estás viendo o un texto que pegues, y calcula un puntaje de riesgo de 0 a 100 combinando:

- Dos modelos de IA (Random Forest + RoBERTa) entrenados para reconocer patrones de phishing en URLs y HTML
- VirusTotal — reputación de la URL entre decenas de motores antivirus
- Google Safe Browsing — listas de sitios maliciosos de Google
- Google Fact Check Tools — verificación de afirmaciones en el contenido
- Antigüedad y datos WHOIS del dominio
- Señales estructurales de la página (formularios sospechosos, campos ocultos, uso de HTTPS, etc.)

El resultado se muestra con un veredicto claro (bajo/medio/alto riesgo) y las razones concretas detrás del puntaje — no es una caja negra.

Funciones:
- Análisis de URL con un clic desde el popup o el panel lateral
- Análisis de contenido: pega cualquier texto para evaluar su confiabilidad
- Historial reciente de análisis
- 100% bajo demanda: la extensión no analiza páginas automáticamente ni recolecta tu navegación

(Nota: Partner Center también ofrece un botón "Generate with AI" para redactar la descripción a partir del paquete subido — se puede usar como punto de partida y luego editar.)

## Categoría sugerida

Herramientas de productividad / Seguridad

## Assets requeridos

| Asset | Requisito | Estado |
|---|---|---|
| **Extension logo** (por idioma) | 1:1, recomendado 300×300, mínimo 128×128 | Generar `icon300.png` (ver `scripts/generate_extension_icons.py`) |
| **Screenshots** | Opcional, máx. 6, tamaño 640×480 o 1280×800 | Pendiente — capturar popup/sidebar en uso |
| **Small/large promotional tile** | Opcional, 440×280 / 1400×560 | Omitir por ahora |

## Sección Privacy (Single Purpose, permisos, datos, política)

**Single Purpose**: "Analiza, a petición del usuario, la URL de la pestaña activa o un texto pegado, para estimar si corresponde a phishing o contenido no confiable, combinando modelos de IA y servicios de threat intelligence."

**Permission justification** (Partner Center pide una justificación por cada permiso declarado en el manifest):

| Permiso | Justificación |
|---|---|
| `activeTab` | Leer la URL de la pestaña activa (vía `chrome.tabs.query`) que el usuario decide analizar al pulsar el botón. |
| `scripting` | Ejecuta un script en la página activa para extraer su texto visible cuando el usuario usa la pestaña de "Análisis de contenido". |
| `clipboardRead` | Permite pegar directamente una URL o texto copiado en el panel de análisis. |
| `storage` | Guarda localmente (chrome.storage.sync) la URL del backend y la API key configuradas por el usuario en Opciones. |
| `sidePanel` | Muestra el panel lateral con el análisis detallado (pestañas URL / Contenido). |

**¿Usa código remoto?**: No — todo el código JS está empaquetado en la extensión; el backend solo recibe/devuelve datos (JSON), no envía código ejecutable.

**Data usage**: marcar "Website content" (URL/texto analizado) como recolectado, usado únicamente para proveer la funcionalidad principal, no compartido con fines publicitarios ni vendido.

**Privacy Policy URL**: `https://github.com/melsysdev-web/phishing_ia/blob/main/PRIVACY_POLICY.md`

## Availability → Visibility

**Hidden** (equivalente al "Unlisted" de Chrome): no aparece en búsquedas ni al navegar la tienda; solo accesible con el link directo del listado (disponible en el Overview de la extensión en Partner Center). Se puede pasar a "Public" más adelante sin perder usuarios ya instalados.

## Proceso de revisión

Hasta 7 días hábiles ("certification"). En **Notes for certification** conviene aclarar que el backend (`https://phishing-ia-2.onrender.com`) puede tardar ~30-60s en la primera respuesta si estuvo inactivo (cold start de Render free tier).
