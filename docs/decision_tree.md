# Árbol de Decisiones de Riesgo

```mermaid
flowchart TD

A[URL Analizada]

A --> B{HTTPS válido}

B -->|No| R1[Incrementar Riesgo]

B -->|Sí| C

C --> D{Dominio recién creado}

D -->|Sí| R2[Incrementar Riesgo]

D -->|No| E

E --> F{Uso de IP}

F -->|Sí| R3[Incrementar Riesgo]

F -->|No| G

G --> H{VirusTotal limpio}

H -->|No| R4[Alto Riesgo]

H -->|Sí| I

I --> J{Google Safe Browsing limpio}

J -->|No| R5[Alto Riesgo]

J -->|Sí| K

K --> L{RoBERTa detecta phishing}

L -->|Sí| R6[Alto Riesgo]

L -->|No| SAFE[Sitio Seguro]
```

## Factores Positivos

* HTTPS válido
* Dominio antiguo
* Reputación limpia
* Sin formularios sospechosos

## Factores Negativos

* Dominio nuevo
* Formularios de login
* Uso de IP
* Palabras asociadas a phishing
* Reportes de malware
