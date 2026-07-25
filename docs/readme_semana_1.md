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

**Diagrama:**

> Ver `docs/architecture_diagram.png`.

---

## 8. Arquitectura Objetivo

**Archivo sugerido:** `docs/arquitectura-objetivo.md`

**Elementos esperados:**

- API inteligente — **ya existe** (`POST /predict`, `POST /analyze-content`)
- Separación entre interfaz, backend, IA y datos — **ya existe** (`extension/` vs `backend/app/{services,ml,random_forest,roberta}` vs `models/`/`datasets/`)
- Pruebas mínimas — **parcial**: existen `tests/` y `backend/tests/`, falta cobertura del pipeline completo de `/predict`
- Variables de entorno — **parcial**: existen y se usan (`core/config.py`), falta `.env.example` versionado
- Contenedor o estrategia de despliegue — **pendiente**: no hay Dockerfile
- Logs, métricas o evidencia operacional — **parcial**: solo se mide `analysis_time_ms` total, no por sub-servicio; no hay logging estructurado
- Consideraciones de seguridad — **parcial**: existe `X-API-Key` opcional y CORS configurable; falta rate limiting propio y forzar HTTPS en producción

**Diagrama:**

> Insertar imagen o enlace al diagrama objetivo (a construir en semanas siguientes).

---

## 9. Estructura del Repositorio

```text
phishing_ia/
  backend/app/
    api/routes.py                # Endpoints FastAPI
    main.py                      # Entry point, CORS
    core/                        # config.py (env vars), security.py (API key)
    services/                    # PhishingService, RiskEngine, VT/SB/FactCheck, ContentClassifier
    ml/fusion/fusion_engine.py   # Combinador ponderado RF + RoBERTa
    random_forest/               # Predictor + loader del modelo RF
    roberta/                     # Predictor URL + entrenadores de contenido
    analyzers/                   # Fetch de HTML + extracción de features
    utils/                       # Features de URL, WHOIS, feature mapper, caché
    schemas/                     # Modelos Pydantic de request/response
  extension/                     # Chrome MV3: popup, sidebar, options, api_client.js
  phishing_detector/             # Módulo standalone de fine-tuning (no integrado aún)
  models/                        # Modelos entrenados (.pkl, carpetas HuggingFace) — no versionado
  datasets/                      # Datasets de entrenamiento
  scripts/                       # CLIs de entrenamiento y generación de reportes
  tests/ · backend/tests/        # Pruebas
  docs/                          # Documentación (arquitectura, seguridad, esta guía)
  requirements.txt
  README.md
```

**Notas sobre la estructura:**

> `backend/app/` sigue una arquitectura en capas (`api` → `services` → `ml`/`random_forest`/`roberta`/`analyzers`/`utils`) sin saltarse niveles. `phishing_detector/` es deliberadamente independiente del backend: es un laboratorio de fine-tuning con control total del loop de entrenamiento, pensado para explorar una arquitectura propia antes de decidir si reemplaza al RoBERTa actual.

---

## 10. Instalación y Ejecución

### Requisitos previos

- Python: 3.12+
- Gestor de paquetes: `pip` (entorno virtual con `venv`)
- Otros requisitos: Google Chrome (modo desarrollador), cuenta de GitHub con acceso SSH al repo, opcionalmente GPU NVIDIA con CUDA 12.8

### Instalación

```powershell
git clone git@github.com:melsysdev-web/phishing_ia.git
cd phishing_ia
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
venv\Scripts\Activate.ps1
venv\Scripts\pip install -r requirements.txt
```

> Ver `docs/guia_instalacion_ai_phishing_detector.docx` para la guía completa paso a paso (SSH, variables de entorno, modelos, troubleshooting).

### Ejecución

```powershell
venv\Scripts\uvicorn backend.app.main:app --reload
```

Luego cargar `extension/` en `chrome://extensions/` con el modo desarrollador activado.

### Variables de entorno

| Variable | Descripción | Obligatoria |
|---|---|---|
| `VIRUSTOTAL_API_KEY` | Clave de la API de VirusTotal v3 | No (degrada esa señal si falta) |
| `SAFE_BROWSING_API_KEY` | Clave de Google Safe Browsing v4 | No |
| `FACT_CHECK_API_KEY` | Clave de Google Fact Check Tools | No |
| `API_KEY` | Clave propia para proteger el backend (header `X-API-Key`) | No (vacío = sin autenticación) |
| `ALLOWED_ORIGINS` | Orígenes CORS adicionales separados por coma | No |

---

## 11. Datos Utilizados

| Fuente de datos | Tipo de datos | Uso dentro del proyecto | Observaciones |
|---|---|---|---|
| Datasets locales en `datasets/` (URLs de phishing/legítimas) | Tabular / texto | Entrenamiento de Random Forest y RoBERTa URL | Origen no documentado en el repo; verificar licencia antes de publicar |
| `GonzaloA/fake_news` (HuggingFace) | Texto (noticias) | Entrenamiento del clasificador de contenido en inglés | Dataset público |
| VirusTotal / Safe Browsing / Fact Check / WHOIS | APIs en tiempo real | Señales de reputación consultadas por URL analizada | Datos de terceros, sujetos a rate limits y disponibilidad |
| HTML de la página analizada | Scraping en vivo | Extracción de features (título, campos de contraseña, etc.) y texto para el clasificador de contenido | Se descarga en tiempo real desde la URL que ingresa el usuario; puede incluir contenido sensible incidental |

**Consideraciones:**

- Los datasets de entrenamiento son públicos o de origen no documentado (pendiente aclarar); no se han detectado datos personales dentro de ellos.
- El HTML scrapeado en vivo puede contener formularios o texto sensible de la página objetivo; no se almacena permanentemente (solo en caché TTL de 10 min).
- Los datasets requieren limpieza/normalización (ver `phishing_detector/preprocess.py::normalize_url` para el caso de URLs con percent-encoding o IPs en hex/octal).
- No existe actualmente un pipeline documentado de validación de calidad de los datasets de entrenamiento.

---

## 12. Riesgos Técnicos y Deuda Técnica

| Riesgo | Categoría | Probabilidad | Impacto | Mitigación propuesta |
|---|---|---|---|---|
| La consulta WHOIS no tiene timeout configurado; puede colgar toda la respuesta de `/predict` | Código | Media | Alto | Agregar timeout explícito o mover a un hilo cancelable dentro del `ThreadPoolExecutor` |
| `torch`/`torchvision`/`torchaudio` fijados a build `+cu128`; falla el `pip install` en máquinas sin esa GPU/CUDA | Despliegue | Alta | Medio | Publicar requirements separados (CPU/GPU) o documentar el índice alterno de PyTorch |
| `models/` y `.env` no versionados, sin `.env.example`; el backend no arranca sin `random_forest_v2.pkl` | Configuración / Despliegue | Alta | Alto | Crear `.env.example`, definir dónde se almacenan y distribuyen los artefactos de modelo (release assets, storage compartido) |
| `ContentClassifierService` desconectado del pipeline de `/predict` | Modelo / Código | Media | Medio | Decidir si se integra al análisis de URL o se documenta oficialmente como feature independiente |
| Módulo `phishing_detector/` standalone no integrado a producción | Modelo | Baja | Bajo | Evaluar métricas y decidir fusión con `PhishingService` o descarte formal |
| Caché solo en memoria; se pierde al reiniciar el servidor | Código / Despliegue | Media | Bajo | Evaluar backend de caché persistente (Redis) si el volumen de tráfico lo justifica |
| Sin CI/CD ni pruebas automatizadas del pipeline completo de `/predict` | Código | Alta | Medio | Configurar GitHub Actions con al menos smoke tests de los endpoints |

---

## 13. Plan de Mejora por Semana

| Semana | Mejora esperada | Evidencia esperada |
|---|---|---|
| Semana 2 | Cerrar brechas de contrato de API: `.env.example`, timeout en WHOIS, decisión sobre `ContentClassifierService` en `/predict` | PR con los cambios, prueba manual documentada |
| Semana 3 | Pruebas y CI/CD | Tests de integración de `/predict` y `/analyze-content`, pipeline en GitHub Actions |
| Semana 4 | Contenedor o despliegue | Dockerfile, estrategia de distribución de `models/` |
| Semana 5 | Observabilidad y rendimiento | Logging estructurado por sub-servicio, métricas de latencia individuales (no solo `analysis_time_ms` total) |
| Semana 6 | Seguridad, documentación y defensa final | README final, demo, presentación |

---

## 14. Limitaciones Actuales

- El clasificador de contenido (fake news) no participa del análisis automático de una URL; requiere que el usuario pegue texto manualmente en una pestaña separada.
- El módulo de fine-tuning standalone (`phishing_detector/`) está implementado pero no se usa en producción.
- No hay métricas de evaluación (precision/recall/F1/AUC-ROC) versionadas para los modelos actualmente en producción (`random_forest_v2.pkl`, `roberta_phishing_new/`).
- La caché es solo en memoria y se pierde al reiniciar el servidor.
- No existe containerización ni pipeline de CI/CD.
- `models/` y `.env` no están versionados en git, lo que complica levantar el proyecto en una máquina nueva sin coordinación manual.
- La consulta WHOIS no tiene timeout, lo que puede bloquear indefinidamente una petición si el servidor WHOIS del dominio consultado no responde.
- El nivel gratuito de VirusTotal limita a 4 solicitudes por minuto, lo que puede agotarse rápido en pruebas o demos consecutivas.

---

## 15. Evidencias

| Evidencia | Enlace o ubicación | Descripción |
|---|---|---|
| Documentación de arquitectura | `docs/arquitectura_ai_phishing_detector.docx` | Pipeline completo, tecnologías, ejemplo de respuesta JSON |
| Guía de instalación | `docs/guia_instalacion_ai_phishing_detector.docx` | Instalación desde cero vía GitHub SSH |
| Diagrama de arquitectura | `docs/architecture_diagram.png` | Diagrama visual del pipeline |
| Endpoint probado | `GET /health`, `GET /cache/stats` | Verificación manual de que el backend responde |
| Captura de pantalla | _Pendiente_ | Popup/sidebar de la extensión en uso |
| Video de demo | _Pendiente_ | — |

---

## 16. Créditos y Referencias

- FastAPI, Pydantic v2, Uvicorn
- scikit-learn (`RandomForestClassifier`)
- PyTorch + HuggingFace Transformers
- `distilroberta-base` y `roberta-base` (fine-tuned para este proyecto)
- `GonzaloA/fake_news` (dataset de entrenamiento, HuggingFace)
- `hamzab/roberta-fake-news-classification` (modelo de fallback remoto, HuggingFace)
- VirusTotal API v3, Google Safe Browsing API v4, Google Fact Check Tools API
- `python-whois`, `tldextract`, `BeautifulSoup4` + `lxml`

---

## 17. Checklist de Revisión

SE DEBE REVISAR SI:

- [x] El problema está claramente descrito.
- [x] Se explica quién usará o se beneficiará de la aplicación.
- [x] Se identifica dónde está la IA.
- [x] Se describen entradas y salidas.
- [x] Se documenta el estado actual del proyecto.
- [x] Se incluye arquitectura actual.
- [x] Se incluye arquitectura objetivo.
- [x] Se explica cómo ejecutar el proyecto.
- [x] Se identifican riesgos técnicos.
- [x] Se presenta plan de mejora por semana.
- [x] No se incluyen claves, contraseñas ni tokens privados.
