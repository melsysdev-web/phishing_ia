# Ficha para Chrome Web Store — AI Phishing Detector

Borrador de los textos del formulario del Developer Dashboard. Ajustar antes de enviar si algo no aplica.

## Descripción corta (máx. 132 caracteres)

Analiza la URL o el contenido de la página actual con IA y threat intelligence para detectar phishing en tiempo real.

## Descripción larga

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

## Categoría sugerida

Herramientas / Productividad

## Justificación de permisos (para el formulario de Privacy practices)

| Permiso | Justificación |
|---|---|
| `activeTab` | Necesario para leer la URL de la pestaña que el usuario decide analizar al pulsar el botón. |
| `tabs` | Consultar la pestaña activa (`chrome.tabs.query`) para obtener su URL antes de enviarla al backend de análisis. |
| `scripting` | Ejecuta un script en la página activa para extraer su texto visible cuando el usuario usa la pestaña de "Análisis de contenido". |
| `clipboardRead` | Permite pegar directamente una URL o texto copiado en el panel de análisis, sin que el usuario tenga que teclearlo. |
| `storage` | Guarda localmente (chrome.storage.sync) la URL del backend y la API key configuradas por el usuario en la página de Opciones. |
| `sidePanel` | Muestra el panel lateral con el análisis detallado (pestañas URL / Contenido). |

## Declaración de datos recolectados (Privacy practices → Data usage)

- **Website content** (URL de la página / texto pegado): sí, se envía al backend para el análisis — marcar como "usado para la funcionalidad principal", no compartido con terceros con fines publicitarios.
- **Personally identifiable information**: no se recolecta.
- **Health info, financial info, authentication info, location, etc.**: no aplica.
- **Uso de datos**: solo para proveer la funcionalidad de análisis solicitada por el usuario. No hay analítica de comportamiento, no hay publicidad, no se venden datos.

## URL de política de privacidad

`https://github.com/melsysdev-web/phishing_ia/blob/main/PRIVACY_POLICY.md` (una vez confirmado el push).

## Visibilidad

Unlisted (no listada) — Distribución → Visibility → "Unlisted" en el Developer Dashboard.
