# Mejoras del scoring — estado de implementación

**Última actualización**: 2026-08-20
**Tests**: 324 → 430

Este documento reemplaza al plan original de 4 fases. El plan proponía 7 mejoras;
al implementarlo se separaron en dos grupos: las que se pueden construir hoy y
las que están bloqueadas por falta de datos etiquetados.

---

## Implementado

### 1. Mapeo no-lineal score → probabilidad
`backend/app/services/confidence_calibration.py`

El score 0–100 se mapea a probabilidad de phishing con una sigmoide en vez de
una regla lineal. Cerca de los extremos la curva es plana (0 y 100 ya eran
veredictos claros); cerca de 50 es empinada, que es donde un punto de más o de
menos sí cambia el significado.

### 2. Confianza e incertidumbre explícitas
El campo `confidence` **existía pero era una copia del `score`** — dos conceptos
distintos con el mismo número. Ahora:

| Campo | Significado |
|---|---|
| `score` | 0–100, veredicto (sin cambios) |
| `probability` | 0–1, probabilidad de que sea phishing |
| `probability_interval` | intervalo de confianza de esa probabilidad |
| `confidence` | 0–1, cuánto confiar en este veredicto |
| `score_interval` | rango plausible del score |
| `ml_agreement` | cuánto coinciden Random Forest y RoBERTa |
| `num_signals` | cuántas señales contribuyeron |

La confianza baja cuando los modelos discrepan o hay pocas señales. Un veredicto
confirmado por VirusTotal o Safe Browsing fija `confidence` en 1.0.

### 3. Acuerdo entre modelos
`backend/app/ml/fusion/fusion_engine.py`

`FusionEngine` reporta `model_agreement` = `1 - |rf - roberta|`. Un score
construido sobre dos modelos que dicen cosas opuestas ya no se presenta con la
misma seguridad que uno donde ambos coinciden. Si uno de los dos falla, el
acuerdo se fija en `SINGLE_MODEL_AGREEMENT` (0.6): no hay segunda opinión.

### 4. Escalado dinámico de deltas
`backend/app/services/risk_engine.py`

La penalización por dominio nuevo (−30) es la mayor fuente de falsos positivos:
un sitio legítimo recién registrado comparte esa señal con el phishing. Cuando
VirusTotal **y** Safe Browsing coinciden en que la URL está limpia, la
penalización se multiplica por `_YOUNG_DOMAIN_DAMPING` (0.4).

Se atenúa, no se anula — un dominio nuevo sigue puntuando peor que uno antiguo.
Una amenaza confirmada nunca activa la atenuación.

### 5. Recolección de feedback
`backend/app/services/feedback_store.py` · `POST /feedback` · `GET /feedback/stats`

Registra correcciones de usuarios. **Es la pieza que desbloquea el resto**: sin
datos etiquetados no hay reentrenamiento posible.

Dos decisiones de diseño:
- **La URL se guarda hasheada (SHA-256)**, no en claro. El backend aprende de
  las correcciones sin registrar qué sitios visita cada usuario.
- **Falsos positivos y falsos negativos se cuentan por separado.** Sus costes
  son distintos: bloquear un sitio legítimo molesta; dejar pasar phishing
  expone. Un promedio los mezclaría.

### 6. Framework de A/B testing
`backend/app/core/experiment.py` · `GET /experiment/status`

Reparte tráfico entre la variante actual y una candidata, vía
`EXPERIMENT_ROLLOUT`. Por defecto 0.0: inactivo hasta configurarlo.

La asignación es **determinista por hash de URL**. Con asignación aleatoria, la
misma URL podría devolver veredictos distintos, y el cache — que no distingue
variantes — serviría el de quien llegó primero.

`scoring_variant` viaja en la respuesta de `/predict` y se guarda con cada
corrección, así el feedback queda atribuido a la variante que lo produjo.

`/experiment/status` requiere autenticación: publicar el reparto de tráfico en
`/metadata` (que es público) le diría a un atacante qué variante le toca.

---

## Bloqueado por falta de datos

Estas mejoras del plan original **no se implementaron**, y la razón es la misma
en todos los casos: requieren datos etiquetados que hoy no existen. Construirlas
ahora significaría entrenar modelos con etiquetas inventadas.

| Mejora | Qué falta |
|---|---|
| **Pesos aprendidos por señal** (regresión logística) | Correcciones etiquetadas. Escribí el módulo y lo borré: sin datos caía a pesos puestos a mano, sin evidencia detrás, y nadie lo consumía. |
| **Ensemble apilado** (meta-modelo sobre RF + RoBERTa) | Un set de validación etiquetado para entrenar el meta-modelo. |
| **Features cruzadas** (edad × TLD, etc.) | Reentrenar el Random Forest, que necesita el dataset de entrenamiento y validación posterior. |
| **Fine-tuning de RoBERTa en URLs** | Corpus de URLs + presupuesto de GPU (~30 días de trabajo según el plan original). |
| **Graph Neural Network** | Datos de entrenamiento y un cambio de arquitectura mayor. |
| **Active learning** | Un pipeline de etiquetado y personas que etiqueten. |

**El desbloqueo es el mismo para todas**: acumular correcciones vía `/feedback`.
`feedback_store.export_training_rows()` ya devuelve las filas en formato
consumible por un reentrenamiento, para que el dato que se recoge hoy sirva sin
migraciones después.

---

## Sobre las estimaciones de precisión del plan original

El plan original proyectaba una progresión de precisión (85–90% → 96–99%) por
fase. **Esas cifras no tienen respaldo medido**: no hay un set de validación
etiquetado contra el cual medir la precisión actual, así que ni el punto de
partida está verificado.

Lo entregado mejora la *calibración* (qué tan bien la confianza refleja la
certeza real) y reduce una fuente conocida de falsos positivos. Cuantificar la
ganancia requiere el mismo dato etiquetado que bloquea el resto.

---

## Verificación

- 430 tests (106 nuevos), ruff limpio
- Cobertura nueva: calibración, acuerdo entre modelos, escalado dinámico,
  almacén de feedback, endpoints de feedback, asignación de variantes,
  compatibilidad del schema con cache antiguo

---

## Siguientes pasos sugeridos

1. Desplegar y **dejar acumular correcciones** unas semanas
2. Revisar `/feedback/stats`: ¿predominan falsos positivos o negativos?
3. Con volumen suficiente, ajustar los deltas con evidencia en vez de intuición
4. Recién entonces evaluar el ensemble apilado, midiendo contra un baseline real
