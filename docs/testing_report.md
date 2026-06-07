# Reporte de Pruebas MVP

Objetivo:
Validar el funcionamiento del motor de análisis de URLs,
motor de riesgo y modelo de Machine Learning para
detección de phishing.

## Entorno

- Sistema Operativo: Windows 11
- Python: 3.12
- FastAPI: 0.x
- Scikit-Learn: x.x
- Modelo: Random Forest
- Dataset: Phishing Websites Dataset

## TC-001

## TC-001 Google

URL:
https://google.com

Objetivo:
Validar un sitio legítimo.

Resultado Esperado:
LOW

Resultado Obtenido:
LOW

Estado:
✅ APROBADO

TC-002

## TC-002 URL con IP

URL:
http://192.168.1.1/login

Objetivo:
Validar detección de IP.

Resultado Esperado:
HIGH

Resultado Obtenido:
HIGH

Estado:
✅ APROBADO

TC-003

## TC-003 Uso de símbolo @

URL:
https://paypal.com@evil-site.xyz/login

Resultado Esperado:
HIGH

Resultado Obtenido:
HIGH

Estado:
✅ APROBADO