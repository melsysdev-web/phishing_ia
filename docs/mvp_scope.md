# AI Phishing Detector — Alcance del Proyecto

## Descripción General

AI Phishing Detector es una extensión para Google Chrome que detecta sitios de phishing en tiempo real usando un pipeline multi-señal: análisis de URL, información WHOIS, análisis HTML, modelos de Machine Learning y tres APIs externas de inteligencia de amenazas.

---

## Objetivo

Desarrollar una extensión de navegador que clasifique URLs como **Seguro / Sospechoso / Peligroso** mediante:

- Machine Learning (Random Forest + RoBERTa)
- NLP para clasificación de contenido
- Threat Intelligence (VirusTotal, Google Safe Browsing, Fact Check)
- Análisis heurístico de URL y dominio

---

## Estado de Implementación

### Backend ✅

- FastAPI con CORS configurado
- Pipeline paralelo (2 oleadas con `ThreadPoolExecutor`)
- Endpoint `POST /predict` — análisis completo de URL
- Endpoint `POST /analyze-content` — solo clasificación de texto
- Endpoints de cache: `GET /cache/stats`, `DELETE /cache`
- Cache en memoria TTL 10 min, máx. 500 entradas
- Configuración centralizada en `core/config.py`

### Análisis de URL ✅

- 12 features extraídas: HTTPS, IP, `@`, subdominios, longitud URL/path, guiones, query params, caracteres especiales, keywords phishing
- Wrapper WHOIS: edad del dominio, TLD, fecha expiración, registrador

### Análisis HTML ✅

- Fetch del HTML con timeout
- Extracción de: título, favicon, descripción, formularios de contraseña, campos ocultos, cantidad de JS/CSS/imágenes

### Machine Learning ✅

| Modelo | Descripción |
|---|---|
| Random Forest v2 | 14 features URL+HTML, `random_forest_v2.pkl` |
| RoBERTa URL | `distilroberta-base` fine-tuned en URLs (`models/roberta_phishing/`) |
| Content Classifier | Fine-tuned en `GonzaloA/fake_news` (`models/roberta_content/`) |
| FusionEngine | RF × 0.4 + RoBERTa URL × 0.6 |

### Threat Intelligence ✅

| Servicio | Estado |
|---|---|
| VirusTotal v3 | Implementado — verdict: clean/suspicious/malicious |
| Google Safe Browsing v4 | Implementado — detecta MALWARE, SOCIAL_ENGINEERING, UNWANTED_SOFTWARE |
| Google Fact Check Tools | Implementado — verifica reputación del dominio como fuente de noticias |

### Chrome Extension ✅

| Componente | Descripción |
|---|---|
| **Popup** | Input URL manual + botón pegar + gauge animado SVG (0-100) + veredicto |
| **Sidebar** | Análisis completo: veredicto, score, sección ML, Threat Intel, razones, clasificador de contenido |
| **Options** | URL del backend configurable, guardada en `chrome.storage.sync` |
| **Manifest V3** | `storage`, `sidePanel` — sin `tabs`/`activeTab` |

---

## Fuera de Alcance

- Sistema multiusuario / autenticación
- Panel administrativo
- Facturación / monetización
- Kubernetes / deployment cloud
- Aplicación móvil
- Análisis de JavaScript ofuscado en profundidad
- Historial local de URLs analizadas

---

## Resultado

El sistema clasifica sitios como **LOW / MEDIUM / HIGH** mostrando:

- Score numérico 0-100 (gauge visual en popup)
- Lista de razones que explican la clasificación
- Detalles por señal: ML, VirusTotal, Safe Browsing, Fact Check, contenido
- Configuración del backend desde la extensión
