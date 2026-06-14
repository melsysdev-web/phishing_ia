# Reporte de Pruebas

## Entorno

| Componente | Versión |
|---|---|
| Sistema Operativo | Windows 11 Home |
| Python | 3.12 |
| FastAPI | 0.115.x |
| Scikit-Learn | 1.x |
| Transformers | 4.x |
| Chrome | Manifest V3 |
| Modelos activos | `random_forest_v2.pkl`, `roberta_phishing/`, `roberta_content/` |

---

## Pruebas de Backend (`POST /predict`)

### TC-001 — Sitio legítimo conocido

**URL:** `https://google.com`
**Objetivo:** Validar que sitios legítimos reciben LOW risk.
**Resultado esperado:** LOW (score ≥ 80)
**Resultado obtenido:** LOW ✅

---

### TC-002 — URL con dirección IP

**URL:** `http://192.168.1.1/login`
**Objetivo:** Detectar uso de IP en lugar de dominio.
**Resultado esperado:** HIGH
**Resultado obtenido:** HIGH ✅
**Señales activadas:** Sin HTTPS (-20), IP en URL (-30)

---

### TC-003 — Símbolo @ (redirección maliciosa)

**URL:** `https://paypal.com@evil-site.xyz/login`
**Objetivo:** Detectar técnica de engaño mediante `@`.
**Resultado esperado:** HIGH
**Resultado obtenido:** HIGH ✅
**Señales activadas:** Símbolo `@` (-40), TLD sospechoso .xyz (-20)

---

### TC-004 — Dominio con múltiples keywords phishing

**URL:** `http://secure-login-verify-account.xyz/password/reset`
**Objetivo:** Detectar acumulación de palabras clave sospechosas.
**Resultado esperado:** HIGH
**Resultado obtenido:** HIGH ✅
**Señales activadas:** Sin HTTPS (-20), TLD .xyz (-20), keywords phishing (-25), path largo (-10)

---

### TC-005 — Sitio gubernamental

**URL:** `https://sat.gob.mx`
**Objetivo:** Validar TLD .gob como confiable.
**Resultado esperado:** LOW
**Resultado obtenido:** LOW ✅
**Señales activadas:** HTTPS (+10), TLD gov-equivalente (+10)

---

### TC-006 — Dominio recién creado (simulado)

**URL:** `https://oferta-especial-hoy.click/comprar`
**Objetivo:** Penalizar TLD sospechoso y keywords.
**Resultado esperado:** HIGH o MEDIUM
**Resultado obtenido:** HIGH ✅
**Señales activadas:** TLD .click (-20), keywords (-9)

---

### TC-007 — Cache hit

**URL:** `https://google.com` (segunda llamada)
**Objetivo:** Verificar que la segunda solicitud usa cache.
**Resultado esperado:** Respuesta idéntica en < 10ms
**Resultado obtenido:** ✅ Respuesta cacheada, tiempo < 5ms

---

### TC-008 — URL inválida (sin prefijo http)

**URL:** `google.com`
**Objetivo:** Validar que Pydantic rechaza URLs sin prefijo.
**Resultado esperado:** HTTP 422 Unprocessable Entity
**Resultado obtenido:** 422 ✅

---

## Pruebas de Extension

### TC-E001 — Paste button

**Acción:** Copiar `https://example.com`, abrir popup, enfocar input.
**Resultado esperado:** Botón 📋 aparece; al hacer clic pega la URL y lanza análisis.
**Resultado obtenido:** ✅

---

### TC-E002 — Gauge animation

**Acción:** Analizar URL que retorna score 85 (LOW).
**Resultado esperado:** Gauge verde anima desde 0 hasta la posición correcta; número sube de 0 a 85.
**Resultado obtenido:** ✅

---

### TC-E003 — Options page — cambio de backend URL

**Acción:** Abrir ⚙️ Configuración, cambiar URL a `http://localhost:9000`, guardar.
**Resultado esperado:** `api_client.js` usa la nueva URL en las siguientes solicitudes.
**Resultado obtenido:** ✅ Confirmado via DevTools Network tab.

---

### TC-E004 — Sidebar — sección ML

**Acción:** Analizar URL desde sidebar.
**Resultado esperado:** Barras RF / RoBERTa URL / Fusion visibles con porcentajes y colores.
**Resultado obtenido:** ✅

---

## Pruebas de Content Classifier (`POST /analyze-content`)

### TC-C001 — Texto de noticias reales

**Input:** Extracto de artículo de BBC News.
**Resultado esperado:** label: REAL, confidence ≥ 0.70
**Resultado obtenido:** REAL, 0.82 ✅

---

### TC-C002 — Texto sensacionalista/desinformación

**Input:** Texto con afirmaciones falsas y lenguaje alarmista.
**Resultado esperado:** label: FAKE, confidence ≥ 0.70
**Resultado obtenido:** FAKE, 0.91 ✅

---

## Cobertura de Señales

| Señal | Prueba cubierta |
|---|---|
| URL features | TC-002, TC-003, TC-004 |
| WHOIS / dominio | TC-006 (TLD) |
| HTML analysis | Implícito en TC-001 |
| VirusTotal | Requiere API key activa |
| Safe Browsing | Requiere API key activa |
| Fact Check | Requiere API key activa |
| Random Forest | TC-001 a TC-006 |
| RoBERTa URL | TC-001 a TC-006 |
| Content Classifier | TC-C001, TC-C002 |
| Cache | TC-007 |
| Extension UI | TC-E001 a TC-E004 |
