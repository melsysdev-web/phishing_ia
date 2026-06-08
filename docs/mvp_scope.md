# AI Phishing Detector Extension

## Descripción General

AI Phishing Detector es una extensión para Google Chrome que utiliza Inteligencia Artificial, análisis de URLs e inteligencia de amenazas para identificar sitios web legítimos, sospechosos o potencialmente fraudulentos.

El sistema analizará características de la URL, información del dominio, contenido web y fuentes externas de reputación para generar una evaluación de riesgo explicable para el usuario.

---

# Objetivo General

Desarrollar una extensión de navegador capaz de detectar sitios de phishing en tiempo real mediante el uso combinado de:

* Machine Learning
* Procesamiento de Lenguaje Natural (NLP)
* Threat Intelligence
* Análisis heurístico

---

# Objetivos Específicos

* Analizar características de URLs.
* Analizar información WHOIS de dominios.
* Detectar patrones comunes de phishing.
* Consultar servicios de reputación externos.
* Clasificar sitios web según su nivel de riesgo.
* Mostrar explicaciones comprensibles para el usuario.

---

# Alcance del MVP

La primera versión incluirá:

### Backend

* FastAPI
* API REST

### Análisis de URL

* Longitud
* HTTPS
* Uso de IP
* Subdominios
* Guiones
* Caracteres sospechosos

### Análisis de Dominio

* Edad del dominio
* Fecha de creación
* Fecha de expiración
* Registrador

### Machine Learning

* Modelo RoBERTa basado en Hugging Face

### Threat Intelligence

* Google Safe Browsing
* VirusTotal

### Frontend

* Extensión Chrome Manifest V3

---

# Fuera de Alcance

* Sistema multiusuario
* Panel administrativo
* Autenticación
* Facturación
* Kubernetes
* Aplicación móvil

---

# Resultado Esperado

El sistema deberá clasificar sitios como:

* Seguro
* Sospechoso
* Peligroso

Mostrando:

* Porcentaje de confianza
* Evidencias encontradas
* Recomendaciones
