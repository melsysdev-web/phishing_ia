# AI Phishing Detector — Presentación del Proyecto

---

## Diapositiva 1 — El Problema

### El phishing sigue siendo la amenaza #1 en ciberseguridad

Cada día se crean **más de 1.4 millones de sitios web de phishing** a nivel mundial.

El ataque es simple: el atacante copia visualmente un sitio legítimo (tu banco, PayPal, Netflix, el SAT), compra un dominio parecido y espera a que el usuario ingrese sus credenciales. El sitio se ve idéntico. El usuario no nota nada.

**Consecuencias reales:**
- Robo de credenciales bancarias
- Suplantación de identidad
- Pérdida de acceso a cuentas (redes sociales, correo, criptomonedas)
- Instalación de malware desde formularios falsos

**¿Por qué los usuarios caen?**
Porque el ojo humano no puede detectar:
- Un dominio registrado hace 3 días
- Una URL con `@` que redirige a otro servidor
- Un formulario que envía la contraseña a un tercero

---

## Diapositiva 2 — La Solución

### AI Phishing Detector: análisis multicapa en tiempo real

Una **extensión para Google Chrome** que analiza cualquier URL antes de que el usuario interactúe con el sitio. No depende de un solo método — combina **9 señales independientes** para dar un veredicto explicable.

**El usuario recibe:**
- Un score visual de 0 a 100
- Un veredicto: 🟢 SEGURO / 🟡 SOSPECHOSO / 🔴 PELIGROSO
- Las razones exactas que llevaron a esa conclusión

**No bloquea nada automáticamente.** Informa al usuario para que tome la decisión.

---

## Diapositiva 3 — Cómo Funciona (perspectiva del usuario)

```
1. El usuario copia una URL sospechosa
2. Abre la extensión → pega la URL → presiona Analizar
3. En 3–8 segundos recibe:
   • Una rueda animada con el score (ej: 23/100)
   • El veredicto: PELIGROSO
4. Abre el panel lateral para ver los detalles:
   • "VirusTotal: 7 motores lo marcan como malicioso"
   • "Dominio creado hace 4 días"
   • "Contiene símbolo @ — posible redirección falsa"
   • "ML: modelos predicen phishing con 91% de confianza"
```

No requiere conocimientos técnicos. Las razones están en español y en lenguaje natural.

---

## Diapositiva 4 — Las 9 Señales del Análisis

El sistema no depende de una sola fuente. Si VirusTotal no tiene datos del dominio nuevo, la IA y el análisis de URL siguen funcionando.

| # | Señal | Qué detecta |
|---|---|---|
| 1 | **Análisis de URL** | IP en URL, símbolo @, subdominios excesivos, keywords phishing, longitud anormal |
| 2 | **WHOIS / Dominio** | Edad del dominio (dominios nuevos = mayor riesgo), TLD sospechoso (.xyz, .click) |
| 3 | **Análisis HTML** | Formularios de contraseña, campos ocultos, exceso de JavaScript |
| 4 | **VirusTotal** | Consulta 70+ antivirus y herramientas de reputación |
| 5 | **Google Safe Browsing** | Lista negra de Google: malware, phishing, software no deseado |
| 6 | **Google Fact Check** | Reputación del dominio como fuente de noticias (detecta desinformación) |
| 7 | **RoBERTa URL** | Modelo de IA entrenado en miles de URLs de phishing — detecta patrones en el string |
| 8 | **Random Forest** | Modelo clásico ML con 14 features combinadas de URL + HTML |
| 9 | **Clasificador de Contenido** | Analiza el texto de la página — detecta contenido falso o engañoso |

Los modelos 7 y 8 se combinan con pesos (60%/40%) en el **FusionEngine** antes de pasarlo al motor de riesgo.

---

## Diapositiva 5 — El Score: Cómo se Calcula

El sistema no vota — **suma evidencias**.

```
Score base: 50 puntos

Cada señal ajusta el score hacia arriba o hacia abajo:

  HTTPS válido           → +10
  Sin HTTPS              → −20
  IP en lugar de dominio → −30
  Símbolo @ en URL       → −40   ← señal muy fuerte
  Dominio < 30 días      → −30
  VirusTotal malicious   → −40
  Safe Browsing amenaza  → −50   ← señal más fuerte
  ML predice phishing    → −30
  Dominio > 10 años      → +20
  VirusTotal limpio      → +10

Resultado: score entre 0 y 100
  ≥ 80  →  LOW     (Seguro)
  50-79 →  MEDIUM  (Sospechoso)
  < 50  →  HIGH    (Peligroso)
```

Este enfoque es **transparente y explicable**: cada puntuación tiene una razón visible para el usuario.

---

## Diapositiva 6 — La Inteligencia Artificial

### ¿Qué modelos usa y por qué?

**Random Forest**
- Modelo clásico de Machine Learning, muy interpretable
- Entrenado con 14 features extraídas de URLs reales y HTML de páginas
- Alta velocidad, sin GPU necesaria

**RoBERTa URL Classifier**
- Modelo de lenguaje (NLP) basado en `distilroberta-base`
- Fine-tuned en miles de URLs etiquetadas como phishing o legítimas
- Detecta patrones lingüísticos que el RF no captura (ej: variaciones sutiles de dominios)

**Content Classifier**
- RoBERTa fine-tuned en el dataset `GonzaloA/fake_news`
- Analiza el texto de la página, no solo la URL
- Un sitio puede tener URL limpia pero contenido de desinformación

**¿Por qué combinar modelos?**
Cada modelo comete errores distintos. Al combinarlos (Fusion Engine: RF × 0.4 + RoBERTa × 0.6) se reducen los falsos positivos y negativos.

---

## Diapositiva 7 — Preguntas Frecuentes del Público

---

### ❓ "¿No hace lo mismo que el antivirus de Chrome?"

**No.** Google Safe Browsing (que usa Chrome internamente) es una lista negra reactiva: solo detecta sitios **ya reportados**. Un sitio de phishing nuevo creado hoy no está en esa lista todavía.

AI Phishing Detector **analiza proactivamente** con IA:
- Detecta dominios nuevos por su edad (WHOIS)
- Detecta patrones de URL que los humanos no notarían
- Detecta el contenido de la página, no solo la URL

Y además también **incluye** Google Safe Browsing como una de sus 9 señales.

---

### ❓ "¿Mis URLs son enviadas a servidores externos?"

**Parcialmente, por diseño y con transparencia:**

- VirusTotal, Google Safe Browsing y Fact Check reciben la URL (estas son APIs de seguridad públicas diseñadas para esto).
- El análisis de IA (RoBERTa, Random Forest) corre **localmente en el servidor del usuario** — las URLs no salen del entorno propio.
- El backend puede instalarse en cualquier servidor o máquina local.

Para uso personal: el backend corre en `localhost`, las URLs nunca salen de tu computadora (excepto a las APIs externas que ya tienen políticas de privacidad).

---

### ❓ "¿Qué tan rápido es?"

- URLs ya analizadas: **< 5 ms** (cache en memoria)
- Primera análisis de una URL: **3 a 8 segundos** (dominado por WHOIS y las APIs externas)
- Las 9 señales corren en paralelo — no secuencialmente

---

### ❓ "¿Puede equivocarse?"

**Sí.** Ningún sistema de detección es perfecto. Existen dos tipos de error:

- **Falso positivo**: marca como peligroso un sitio legítimo → el usuario puede ignorar la advertencia
- **Falso negativo**: no detecta un sitio de phishing nuevo → el riesgo permanece

Por eso el sistema **informa, no bloquea**. El usuario siempre toma la decisión final. Y al mostrar las razones, el usuario puede juzgar si el resultado tiene sentido.

---

### ❓ "¿Por qué usar IA si ya existe VirusTotal?"

VirusTotal depende de que alguien haya **reportado** la URL antes. Un atacante puede crear 100 dominios nuevos hoy, usarlos durante 24 horas y luego abandonarlos. VirusTotal no los conoce.

La IA detecta **el patrón**, no la URL específica. Un dominio como `paypa1-secure-login.click` registrado hace 2 horas puede ser detectado por:
- La edad del dominio (2 horas → −30)
- El TLD `.click` (−20)
- La keyword `login` + `secure` + `paypal` (−25)
- RoBERTa URL reconoce el patrón lingüístico de dominios de phishing

Resultado: HIGH, aunque VirusTotal no tenga información todavía.

---

### ❓ "¿Funciona con sitios en español?"

**Sí.** El análisis de URL y WHOIS es agnóstico al idioma. Las APIs externas cubren dominios globalmente. El clasificador de contenido fue entrenado principalmente en inglés, pero existe un trainer en español (`content_trainer_es.py`) para extender la cobertura.

---

### ❓ "¿Cuánto cuesta usar esto?"

El backend y la extensión son **software propio, sin costo de licencia**.

Las APIs externas tienen planes gratuitos con límites:
- VirusTotal: 4 solicitudes/minuto (gratuito)
- Google Safe Browsing: 10,000 solicitudes/día (gratuito)
- Google Fact Check: incluido en Google Cloud (con cuota gratuita)

Para uso personal o demostrativo: **costo cero**.

---

### ❓ "¿Qué diferencia tiene con un bloqueador de anuncios?"

Los bloqueadores de anuncios (uBlock, AdBlock) operan con **listas de dominios conocidos** que se actualizan periódicamente. No analizan contenido en tiempo real ni usan IA. No detectan dominios nuevos de phishing no reportados.

AI Phishing Detector es un **sistema de análisis activo**, no una lista de bloqueo.

---

### ❓ "¿Puede analizar correos electrónicos o no solo URLs?"

Actualmente analiza **URLs** (endpoint `POST /predict`) y **texto libre** (endpoint `POST /analyze-content`). Un correo electrónico podría analizarse extrayendo sus URLs y pegando el cuerpo del texto en el clasificador de contenido. La integración directa con clientes de correo es una posible expansión futura.

---

### ❓ "¿Qué pasa si el backend no está corriendo?"

La extensión muestra un error descriptivo: _"No se pudo conectar al servidor. Verifica la URL en ⚙️ Configuración."_ No falla silenciosamente. La página de opciones permite cambiar la URL del backend (útil si se despliega en un servidor remoto).

---

## Diapositiva 8 — Casos de Uso Reales

| Escenario | Cómo ayuda |
|---|---|
| Recibes un link por WhatsApp diciendo "tu paquete está detenido" | Pegas la URL → HIGH, dominio de 1 día, TLD sospechoso |
| Un mail de "tu banco" te pide verificar tu cuenta | Pegas la URL del botón → formulario de contraseña detectado, dominio diferente al banco real |
| Sitio de noticias viral en redes sociales | Clasificador de contenido detecta lenguaje de desinformación → FAKE 87% |
| Tienda online desconocida con precios muy bajos | Dominio nuevo + sin favicon + TLD .shop → MEDIUM/HIGH |
| Un investigador de seguridad analiza dominios en masa | API REST directa, respuesta JSON estructurada con todos los campos |

---

## Diapositiva 9 — Arquitectura en 30 Segundos

```
[Chrome Extension]
     │  pega URL
     ▼
[FastAPI Backend]  ──→  Cache (respuesta en < 5ms si ya fue analizada)
     │
     ├── [URL Features]  ──────────────────────────┐
     │                                              │
     ├── [WHOIS]         ──┐                       │
     ├── [HTML Parser]   ──┤                       │
     ├── [VirusTotal]    ──┤  Paralelo             ▼
     ├── [Safe Browsing] ──┤  (6 workers)    [Risk Engine]
     ├── [Fact Check]    ──┤                  Score 0-100
     ├── [RoBERTa URL]   ──┘                  LOW/MEDIUM/HIGH
     │                                         + Razones
     ├── [Random Forest] ──┐  Paralelo
     └── [Content ML]    ──┘  (2 workers, depende del HTML)
              │
              └── [FusionEngine: RF×0.4 + RoBERTa×0.6]
```

---

## Diapositiva 10 — Próximos Pasos

| Mejora | Descripción |
|---|---|
| Historial local | Guardar URLs analizadas en `IndexedDB` dentro de la extensión |
| Análisis automático | Opción en settings para analizar la pestaña activa al cargar |
| Modo oscuro | Tema oscuro en popup y sidebar |
| Exportar reporte | Generar PDF con el análisis completo |
| Deploy en la nube | Backend en Railway/Render para que funcione sin servidor local |
| Dataset en español | Ampliar el clasificador de contenido con noticias falsas en español |
| Alertas por nivel | Notificación del sistema cuando se detecta HIGH risk |

---

## Resumen Ejecutivo

> **AI Phishing Detector** es una extensión de Chrome que combina 9 señales de análisis — incluyendo 3 modelos de Machine Learning y 3 APIs de inteligencia de amenazas — para evaluar el riesgo de phishing de cualquier URL en tiempo real. Da un score de 0 a 100 con razones en lenguaje natural, sin bloquear automáticamente ni enviar datos a terceros fuera de las APIs de seguridad estándar. El backend corre localmente y puede desplegarse en cualquier servidor.
