# AI Phishing Detector

## 1. Información General

**Módulo:** Módulo 4 - Desarrollo de Aplicaciones con IA
**Semana:** Semana 1 - Diagnóstico y arquitectura inicial
**Nombre del equipo:**
**Integrantes:**

- Integrante 1: Melvin Rodriguez
- Integrante 2: Eskin Montiel
- Integrante 3: Katia Orellana

---

## 2. Descripción del Problema

**Preguntas guía:**

- ¿Qué problema real se quiere resolver?
- ¿A quién afecta este problema?
- ¿En qué contexto ocurre?
- ¿Por qué una solución con IA puede aportar valor?

**Descripción:**

> El phishing es uno de los vectores de ataque más comunes en internet: páginas que suplantan bancos, redes sociales o servicios de correo para robar credenciales o datos financieros. Las listas negras tradicionales (blacklists estáticas) reaccionan tarde porque un dominio de phishing puede estar activo solo unas horas antes de ser reportado y bloqueado, y las reglas fijas son fáciles de evadir con pequeñas variaciones (subdominios, acortadores, homografía Punycode, etc.).
>
> Afecta principalmente a usuarios de internet sin formación técnica en seguridad, que reciben enlaces por correo, WhatsApp o redes sociales y no tienen forma rápida de verificar si un sitio es legítimo antes de introducir sus datos. Ocurre en el contexto de la navegación diaria (banca en línea, redes sociales, compras) donde la decisión de confiar o no en una URL se toma en segundos.
>
> Una solución con IA aporta valor porque puede generalizar patrones que no están en ninguna lista negra: un modelo entrenado sobre miles de URLs de phishing aprende regularidades estructurales (longitud, uso de IP, subdominios, antigüedad del dominio, texto de la página) que permiten anticipar amenazas nuevas ("zero-day phishing") en lugar de depender únicamente de reportes previos.

---

## 3. Usuarios o Beneficiarios

| Usuario / Beneficiario | Necesidad principal | Cómo ayuda la aplicación |
|---|---|---|
| Usuario final no técnico navegando la web | Saber rápidamente si un enlace es seguro antes de hacer clic o introducir datos | Extensión de Chrome con veredicto visual (LOW/MEDIUM/HIGH) y razones en lenguaje natural, sin necesitar conocimientos técnicos |
| Usuario que recibe contenido dudoso (noticias, publicaciones) | Verificar si un texto parece verídico o fabricado | Pestaña de análisis de contenido (REAL/FAKE) sobre texto pegado o extraído de la página activa |
| Persona con curiosidad/analista informal de seguridad | Entender *por qué* una URL es sospechosa, no solo un puntaje | Lista de razones ordenadas por impacto (ej. "Dominio creado hace menos de 30 días", "VirusTotal: 5 motores lo marcan como malicioso") |

---

## 4. Descripción de la Solución

**Preguntas guía:**

- ¿Qué permite hacer la aplicación?
- ¿Qué recibe como entrada?
- ¿Qué entrega como resultado?
- ¿Qué parte del proceso automatiza o mejora?

**Descripción:**

> La aplicación es una extensión de Chrome (Manifest V3) respaldada por un backend en FastAPI que analiza una URL o un texto y determina si representa un riesgo de phishing o desinformación.
>
> **Entrada:** una URL (`http://` o `https://`) desde el popup o el sidebar de la extensión, o texto libre pegado/extraído de la página activa para el análisis de contenido.
>
> **Salida:** para URLs, un score de 0 a 100 con veredicto `LOW` / `MEDIUM` / `HIGH`, una lista de razones legibles que explican el resultado, y el detalle de cada señal individual (WHOIS, HTML, VirusTotal, Safe Browsing, Fact Check, modelos ML). Para texto libre, un veredicto `REAL`/`FAKE` con nivel de confianza.
>
> **Qué automatiza:** reemplaza el proceso manual que un usuario tendría que hacer por su cuenta (revisar WHOIS, buscar el dominio en VirusTotal, fijarse en la antigüedad, leer la URL en busca de trucos como `@` o IPs, revisar Safe Browsing) y lo condensa en un solo análisis paralelo que tarda entre 3 y 8 segundos, con resultados cacheados 10 minutos para URLs repetidas.

---

## 5. Componente de Inteligencia Artificial

| Elemento | Descripción |
|---|---|
| Tipo de IA utilizada | Sistema híbrido: modelo de ensamble clásico (Random Forest) + modelo de lenguaje (Transformer fine-tuned) combinados por un motor de fusión ponderado, cuya salida alimenta un motor de reglas expertas (RiskEngine) |
| Modelo, algoritmo, servicio o técnica | (1) `RandomForestClassifier` (scikit-learn) entrenado sobre 18 features de URL+HTML; (2) `distilroberta-base` fine-tuned para clasificación binaria phishing/legítimo directamente sobre el string de la URL; (3) `roberta-base` fine-tuned para clasificación de noticias falsas (REAL/FAKE), con fallback a `hamzab/roberta-fake-news-classification` de HuggingFace; (4) `FusionEngine` combina RF (40%) y RoBERTa (60%) con degradación automática si uno falla |
| Datos de entrada | URL en texto plano (para RoBERTa URL), 18 features numéricas derivadas de la URL y del HTML de la página (para RF: longitud, uso de IP, símbolo `@`, HTTPS, número de subdominios, presencia de campo de contraseña, etc.), texto libre de artículo/página (para el clasificador de contenido) |
| Resultado generado por la IA | Probabilidad de phishing (0–1) por cada modelo, combinada en `phishing_probability` por el `FusionEngine`; esa probabilidad se convierte en una de las señales que el `RiskEngine` suma/resta sobre una base de 50 puntos hasta un score final 0–100 |
| Métrica o forma de evaluación, si aplica | El módulo experimental `phishing_detector/` (standalone, no integrado en producción) incluye `evaluate_model()` con precision, recall, F1 y AUC-ROC. Los modelos actualmente en producción (`random_forest_v2.pkl`, `roberta_phishing_new/`) no tienen un reporte de métricas versionado en el repositorio — es una brecha a cerrar en próximas semanas |
| Limitaciones actuales | El clasificador de contenido (fake news) **no está conectado** al pipeline de análisis de URL (`/predict`); solo se invoca desde el endpoint separado `/analyze-content`. El módulo standalone `phishing_detector/` con fine-tuning propio está implementado pero no integrado a `PhishingService`. No hay métricas de evaluación versionadas para los modelos en producción. No hay monitoreo de drift de los modelos |

**Explicación breve:**

> La IA participa en dos puntos concretos del pipeline: como predictor de probabilidad de phishing (RF + RoBERTa fusionados) y, de forma independiente, como clasificador de veracidad de contenido. Sin embargo, la decisión final (`LOW`/`MEDIUM`/`HIGH`) no la toma un modelo por sí solo: el `RiskEngine` trata la salida del `FusionEngine` como una señal más entre ~29 reglas heurísticas (antigüedad del dominio, TLD, VirusTotal, Safe Browsing, etc.), lo que hace el resultado más explicable e interpretable que una caja negra pura.

---

## 6. Estado Actual del Proyecto

### Funcionalidades que ya funcionan

- Pipeline completo `POST /predict`: extracción de features de URL, WHOIS, fetch+parseo de HTML, VirusTotal, Google Safe Browsing, Google Fact Check, Random Forest, RoBERTa URL, fusión ponderada y `RiskEngine` con score 0–100 y razones explicables
- Caché en memoria con TTL de 10 minutos (500 entradas máx.), thread-safe
- Endpoint independiente `POST /analyze-content` para clasificación REAL/FAKE de texto libre
- Extensión de Chrome (MV3) funcional: popup con gauge visual, sidebar con dos pestañas (URL y Contenido), página de opciones para configurar la URL del backend, dark mode e historial en el popup
- Degradación elegante: si una API externa o un modelo falla, el resto del pipeline sigue funcionando (`_safe()` wrapper + pesos re-balanceados en `FusionEngine`)

### Funcionalidades incompletas o pendientes

- Integrar `ContentClassifierService` al pipeline de `/predict` (hoy corre aislado, solo vía `/analyze-content`)
- Integrar el módulo standalone `phishing_detector/` (fine-tuning con cabeza personalizada) a `PhishingService`, o documentar formalmente que queda fuera de alcance
- Persistencia de caché fuera de memoria (hoy se pierde al reiniciar el servidor)
- `.env.example` y una estrategia de distribución de `models/` (ninguno de los dos está versionado en git, lo que complica levantar el proyecto en una máquina nueva)
- Timeout en la consulta WHOIS (`domain_utils.py`) — actualmente puede bloquear toda la respuesta de `/predict` si el servidor WHOIS del dominio consultado no responde
- Pipeline de CI/CD y contenedor de despliegue (no existe Dockerfile ni GitHub Actions todavía)

### Evidencias actuales

- `GET /health` responde `{"status": "healthy"}` cuando el backend está arriba
- `GET /cache/stats` expone `entries`, `valid`, `ttl_seconds`, `max_size`
- Ejemplo de respuesta real de `POST /predict` documentado en `docs/arquitectura_ai_phishing_detector.docx`, sección 8.2
- Extensión probada manualmente en Chrome (modo desarrollador) contra el backend local

---

## 7. Arquitectura Actual

**Archivo sugerido:** `docs/architecture.md`, `docs/arquitectura_ai_phishing_detector.docx`

**Componentes actuales:**

| Componente | Descripción | Estado actual |
|---|---|---|
| Interfaz | Extensión Chrome MV3 (popup + sidebar + opciones), vanilla JS | Funcional |
| Backend / lógica principal | FastAPI + `PhishingService` (orquestador) + `RiskEngine` (scoring por reglas) | Funcional |
| Componente IA | Random Forest + RoBERTa URL + `FusionEngine`; `ContentClassifierService` como servicio aparte | Funcional, pero el clasificador de contenido no está integrado al pipeline principal |
| Datos | Modelos `.pkl` y carpetas HuggingFace en `models/`; datasets de entrenamiento en `datasets/` | Funcional localmente, pero **no versionado en git** (riesgo de portabilidad) |
| Servicios externos | VirusTotal v3, Google Safe Browsing v4, Google Fact Check Tools, WHOIS | Funcional con degradación si faltan claves o hay timeout |
| Configuración | `.env` + `core/config.py`, `X-API-Key` opcional vía `core/security.py` | Funcional, pero falta `.env.example` versionado |