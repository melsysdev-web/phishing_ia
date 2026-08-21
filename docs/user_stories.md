# Historias de Usuario

## HU-001 ✅

**Como** usuario de Chrome
**Quiero** pegar manualmente una URL en la extensión
**Para** conocer si el sitio es seguro antes de ingresar información.

**Criterios de aceptación:**
- Input de URL visible en el popup con placeholder descriptivo
- Botón 📋 aparece al enfocar el input para pegar desde portapapeles
- Si la URL pegada es válida (http/https), el análisis se lanza automáticamente

---

## HU-002 ✅

**Como** usuario
**Quiero** recibir una puntuación de riesgo visual
**Para** tomar decisiones informadas sobre mi navegación.

**Criterios de aceptación:**
- Gauge SVG animado que muestra score 0-100
- Color verde/amarillo/rojo según nivel LOW/MEDIUM/HIGH
- Veredicto en texto: SEGURO / SOSPECHOSO / PELIGROSO

---

## HU-003 ✅

**Como** usuario
**Quiero** visualizar las razones que llevaron a la clasificación
**Para** comprender el resultado generado por la IA.

**Criterios de aceptación:**
- Lista de razones en el sidebar con iconos
- Razones específicas por señal (ML, APIs, URL features, HTML)

---

## HU-004 ✅

**Como** usuario
**Quiero** que se detecten amenazas conocidas
**Para** evitar el robo de credenciales.

**Criterios de aceptación:**
- Integración con VirusTotal v3 (detección por antivirus)
- Integración con Google Safe Browsing v4 (malware, phishing, social engineering)
- Score penalizado significativamente ante detecciones positivas

---

## HU-005 ✅

**Como** usuario
**Quiero** identificar sitios que imitan marcas legítimas
**Para** evitar ataques de phishing.

**Criterios de aceptación:**
- Detección de keywords sospechosas (login, paypal, verify, password…)
- Detección de símbolo `@` para redirecciones engañosas
- RoBERTa URL detecta patrones de phishing en el string de la URL

---

## HU-006 ✅

**Como** investigador de seguridad
**Quiero** visualizar las características extraídas y las puntuaciones de cada modelo
**Para** validar el funcionamiento del sistema.

**Criterios de aceptación:**
- Sidebar muestra sección "Modelos IA" con barras de probabilidad para RF, RoBERTa URL y Fusion
- Sección Threat Intel muestra resultado de cada API externa
- Tab de Contenido muestra clasificación REAL/FAKE con barra de confianza

---

## HU-007 ✅

**Como** usuario
**Quiero** recibir una explicación clara del riesgo detectado
**Para** entender las recomendaciones del sistema.

**Criterios de aceptación:**
- Texto de ayuda debajo del gauge ("Esta URL parece segura" / "Esta URL tiene señales sospechosas" / "Esta URL es peligrosa")
- Razones en lenguaje natural, no códigos técnicos

---

## HU-008 ✅

**Como** administrador del proyecto
**Quiero** poder actualizar modelos de IA
**Para** mejorar continuamente la precisión del sistema.

**Criterios de aceptación:**
- Scripts de entrenamiento independientes en `backend/app/roberta/` y `training/`
- Modelos guardados en `models/` y cargados automáticamente al iniciar el backend

---

## HU-009 ✅

**Como** usuario
**Quiero** configurar la URL del backend desde la extensión
**Para** poder usar el sistema con un servidor propio o remoto.

**Criterios de aceptación:**
- Página de opciones accesible desde el botón ⚙️ en popup y sidebar
- URL del backend guardada en `chrome.storage.sync` (persiste entre sesiones)
- Botón "Probar conexión" con feedback visual
- Botón "Restablecer" vuelve a `http://localhost:8000`

---

## HU-010 ✅

**Como** usuario
**Quiero** un panel lateral con el análisis completo
**Para** ver todos los detalles sin que el popup quede saturado de información.

**Criterios de aceptación:**
- Sidebar con dos tabs: URL (análisis completo) y Contenido (clasificador de texto)
- Veredicto, score bar, sección ML, Threat Intel y razones completas
- Accesible desde el botón de side panel de Chrome

---

## HU-011

**Como** usuario
**Quiero** que el análisis de contenido detecte noticias falsas
**Para** identificar sitios que difunden desinformación.

**Criterios de aceptación:**
- Tab "Contenido" en sidebar permite pegar texto para analizar
- Clasificador retorna REAL/FAKE con porcentaje de confianza
- Score del URL penalizado si el contenido es clasificado como FAKE con alta confianza
- Endpoint independiente `POST /analyze-content` para uso programático

**Estado:** ✅ Implementado (modelo en `models/roberta_content/`)
