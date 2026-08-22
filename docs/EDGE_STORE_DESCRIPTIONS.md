# Textos para la ficha de Edge Add-ons

**Versión**: 1.0.0 (publicación nueva, no una actualización)
**Idioma de la ficha**: español — la interfaz de la extensión está enteramente en español (`lang="es"`)
**Actualizado**: 2026-08-21

> **Dos reglas de Edge que este documento respeta y conviene no romper al editarlo:**
> 1. **No mencionar otros navegadores** (Chrome, Firefox, Safari) en ningún texto de la ficha. La versión anterior de este archivo listaba "Google Chrome (v120+)" en una tabla de compatibilidad; era motivo de rechazo.
> 2. **No prometer lo que no existe.** Las descripciones antiguas anunciaban animaciones que dependían de anime.js, retirado el 2026-08-21 por cargar código remoto. Anunciar funciones inexistentes acaba en reseñas negativas.

---

## Descripción corta (240 caracteres máx.)

### Español — 197/240

```
Analiza si una web es phishing combinando IA, VirusTotal y Google Safe
Browsing. Puntuación de 0 a 100 con los motivos de cada veredicto. Solo
analiza cuando tú se lo pides. Gratuito y de código abierto.
```

### Inglés — 198/240

```
Checks whether a site is phishing using AI, VirusTotal and Google Safe
Browsing. Get a 0-100 risk score with the reasons behind every verdict.
Analyzes only when you ask it to. Free and open source.
```

---

## Descripción larga

```
AI Phishing Detector te dice si la página que estás viendo es de fiar.

Pulsa el icono y la extensión analiza la URL de la pestaña actual. En unos
segundos obtienes una puntuación de riesgo de 0 a 100, un veredicto claro
(bajo, medio o alto) y —lo más importante— los motivos concretos que lo
sustentan: no es una caja negra.

QUÉ MIRA

· Dos modelos de aprendizaje automático entrenados sobre URLs de phishing
  reales (Random Forest y RoBERTa), que combinan sus resultados
· VirusTotal: si el sitio ya fue denunciado por otros motores
· Google Safe Browsing: la lista de Google de sitios peligrosos
· Antigüedad y registro del dominio: los dominios recién creados son una de
  las señales más fuertes de phishing
· Estructura de la URL y contenido de la página: subdominios sospechosos,
  formularios de acceso, guiones en el dominio

Ninguna señal decide por sí sola. Se combinan, y un sitio recién registrado
pero limpio según VirusTotal y Safe Browsing se penaliza menos, porque los
negocios nuevos son la principal causa de falsas alarmas.

ANÁLISIS DE TEXTO

Además de la URL, puedes enviar texto de la página —extraído con un botón o
pegado por ti— para comprobar si presenta los patrones del contenido
fabricado o engañoso. Verás el texto antes de enviarlo y podrás editarlo.

PRIVACIDAD

· No monitoriza tu navegación. No hay análisis automático: nada se envía
  hasta que pulsas el botón
· Solo sale del navegador la URL o el texto que envías
· El historial de los últimos 10 análisis se guarda en tu equipo y puedes
  borrarlo cuando quieras
· No hay cuentas, ni registro, ni publicidad, ni rastreadores

CÓDIGO ABIERTO

Todo el proyecto —extensión y backend— es público. Puedes revisar el código,
o ejecutar tu propio servidor y apuntar la extensión a él desde las opciones.

NOTA SOBRE LA PRIMERA CONSULTA

El servidor de análisis está en un plan gratuito que se suspende tras un rato
sin uso. El primer análisis después de una pausa puede tardar entre 60 y 90
segundos mientras despierta. Los siguientes son de segundos.
```

---

## Single purpose description

El campo exige un propósito **estrecho y fácil de entender**. Esta versión cubre además los permisos solicitados: si se declara únicamente el análisis de URLs, queda sin explicar por qué la extensión necesita `clipboardRead` y `scripting`.

```
This extension tells the user whether a website is likely to be a phishing or
fraudulent site. When the user clicks it, the extension sends the current
page's URL to its backend, which returns a 0-100 risk score and the reasons
behind it. The user can also submit text from that page for the same
fraud-and-deception check. Nothing is analyzed until the user asks for it.
```

**Riesgo conocido**: la extensión hace dos cosas (detección de phishing y clasificación de contenido engañoso) y un revisor puede leerlas como dos propósitos. El texto las une con el argumento de que ambas responden a *"¿me puedo fiar de esta página?"*. Si hay rechazo, será por aquí; la alternativa es publicar solo el análisis de URL y añadir el de contenido más adelante.

---

## Justificación de permisos (1000 caracteres máx. cada una)

Los siete permisos declarados tienen uso real en el código; ninguno es huérfano.

### storage

```
The extension stores three values with chrome.storage.local: the backend URL,
an optional API key for it, and a boolean recording whether the last
connection check succeeded, so the UI can show connection status without
re-testing every time it opens. The backend URL is configurable because the
project is open source and users can run their own instance instead of the
default one. Separately, the popup keeps the last 10 analyses in localStorage
so the user can see what they recently checked; that list never leaves the
browser and a "clear" button removes it. Nothing is synced to the cloud:
storage.local is used rather than storage.sync so these settings stay on the
user's machine.
```

> El historial vive en `localStorage` (`popup.js:15`), **no** en `chrome.storage`. Omitirlo haría que la justificación pareciese falsa a quien lea el código.

### sidePanel

```
The extension's main interface is a side panel. It stays open beside the page
while the user reads the analysis: the 0-100 risk score, the reasons behind
the verdict, and each individual signal that contributed to it. A popup alone
was not enough, because the report is long and the user needs it visible while
deciding whether to trust the page. The extension only sets
openPanelOnActionClick to false on install; the panel is opened by the user
from the browser's own side-panel control.
```

### clipboardRead

```
The user can submit text to be checked for the deceptive patterns typical of
fraudulent pages. clipboardRead backs a paste button that calls
navigator.clipboard.readText() strictly in response to that click. It never
runs in the background, on page load, or without a direct user action, and the
text is placed in a visible text box that the user can read and edit before
choosing to submit it. The button exists because the text people want checked
is normally already copied from the page they are suspicious about.
```

> El más débil de los siete: solo ahorra un `Ctrl+V`. Si el revisor lo objeta, retirarlo del manifest no elimina ninguna función — el usuario seguiría pegando el texto a mano.

### scripting

```
When the user clicks "extract page content", the extension injects a single
function into the active tab to read that page's visible text. The extracted
text is placed in a textarea where the user can see and edit it before
deciding whether to submit it for analysis. Injection happens only on that
click, only into the tab the user is currently viewing, and the injected
function only reads text — it does not modify the page. Nothing is injected
automatically, and no content script runs on page load.
```

### activeTab

```
The extension analyzes the page the user is currently on, so it needs that
page's URL. When the user clicks it, the extension reads the URL of the active
tab and sends it for the phishing check. activeTab grants this only for the
tab the user invoked the extension on, and only after that interaction, which
is exactly the scope required. The extension does not track browsing, does not
read other tabs, and never queries tabs in the background.
```

### alarms

```
An alarm fires every 5 minutes to call the backend's /health endpoint and
cache the result, so the interface can tell the user immediately whether the
analysis service is reachable. This matters because the backend runs on a free
tier that sleeps after inactivity and takes 60-90 seconds to wake: without the
check, a first analysis after an idle period looks like a broken extension
rather than a cold start. alarms is used instead of setInterval because a
Manifest V3 service worker is terminated when idle and timers do not survive.
```

### Host permission

```
https://phishing-ia-smmy.onrender.com/* is the extension's own backend and the
only remote host it contacts. The URL or text the user submits is sent there
and it returns the risk score with its reasons; the machine-learning models
and the threat-intelligence lookups are far too heavy to run in the browser.
http://localhost/* and https://localhost/* are included because the project is
open source: users can run that same backend on their own machine and point
the extension at it from the options page. No other hosts are requested, and
the extension does not read or modify the pages the user visits.
```

---

## Notes for certification

Sin esta nota el revisor espera 90 segundos, da la extensión por rota y la rechaza.

```
No login or test account is required. Install the extension and click its
icon; it analyzes the current tab.

IMPORTANT — first analysis is slow: the analysis backend runs on a free
hosting tier that suspends the service after inactivity. The first request
after an idle period takes 60-90 seconds while the server wakes up and loads
the machine-learning models. Subsequent analyses take 2-8 seconds. The
extension shows a "waking up the server" notice after 12 seconds so the delay
is not mistaken for a failure. Please allow the first analysis to finish
before evaluating.

How to test:
1. Open any website (for example https://www.wikipedia.org)
2. Click the extension icon
3. Click "Analyze" — a 0-100 risk score appears with the reasons behind it
4. For the content check, open the side panel, use "extract page content",
   then submit the text

The interface is in Spanish.
```

### Credenciales de prueba

No se necesitan. La extensión no tiene login, cuentas ni zonas de pago:

```
No login required. The extension works immediately after installation with no
account, sign-up or configuration.
```

---

## Antes de enviar

- [ ] **El backend acepta peticiones sin autenticar.** El paquete no envía `X-API-Key`; si Render todavía tiene `API_KEY` configurada, *todos* los análisis devuelven 403 y el rechazo es seguro. Requiere `API_KEY` vacía y `ALLOW_UNAUTHENTICATED=true` en el Environment Group
- [ ] Verificado con `venv\Scripts\python scripts\smoke_test.py --base-url https://phishing-ia-smmy.onrender.com` (llama a `/predict`; `/health` no sirve como prueba)
- [ ] Paquete generado con `.\scripts\package_extension.ps1` (nunca comprimir `extension/` a mano)
- [ ] ZIP descomprimido en carpeta limpia y probado desde ahí, no con `load-extension.ps1`
- [ ] Capturas de pantalla listas: mínimo una de 1280×800 o 640×400 (en `docs/store_assets/` solo hay `logo300.png`)
- [ ] Política de privacidad accesible en una URL pública
- [ ] Ningún texto de la ficha menciona otros navegadores
