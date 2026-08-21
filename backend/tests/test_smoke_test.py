"""Tests del smoke test post-despliegue (`scripts/smoke_test.py`).

Un smoke test que aprueba cuando el servicio está roto es peor que no tener
ninguno: da luz verde justo en el caso que existe para detectar. Lo que se
comprueba aquí es sobre todo eso — que no acepte respuestas degradadas.
"""

import pytest

from scripts.smoke_test import _json_o_vacio, analizar, revisar_predict


def _respuesta_sana(**cambios):
    payload = {
        "url": "https://example.com",
        "cached": False,
        "risk_assessment": {"risk": "LOW", "score": 88, "reasons": []},
        "machine_learning": {
            "fusion": {"prediction": 1, "phishing_probability": 0.12},
        },
    }
    payload.update(cambios)
    return payload


def test_una_respuesta_completa_no_da_problemas():
    assert revisar_predict(200, _respuesta_sana()) == []


@pytest.mark.parametrize("status", [500, 502, 503, 504, 403, None])
def test_cualquier_status_que_no_sea_200_falla(status):
    problemas = revisar_predict(status, {})

    assert len(problemas) == 1
    assert str(status) in problemas[0]


def test_detecta_que_ningun_modelo_cargo():
    """El fallo silencioso que motiva todo esto.

    Si los pesos no están o no caben en memoria, cada sub-servicio devuelve
    {"error": ...} vía _safe() y /predict sigue contestando un 200 bien
    formado. Mirar solo el status daría el despliegue por bueno.
    """
    rota = _respuesta_sana(
        machine_learning={"fusion": {"error": "Both models failed"}},
    )

    problemas = revisar_predict(200, rota)

    assert len(problemas) == 1
    assert "Both models failed" in problemas[0]


def test_detecta_una_fusion_sin_probabilidad():
    rota = _respuesta_sana(machine_learning={"fusion": {"prediction": 1}})

    assert revisar_predict(200, rota) == ["la fusión no trae phishing_probability"]


def test_detecta_una_respuesta_sin_risk_assessment():
    problemas = revisar_predict(200, {"url": "https://example.com"})

    assert problemas == ["la respuesta no trae risk_assessment"]


@pytest.mark.parametrize("riesgo", ["UNKNOWN", "", None, "low"])
def test_rechaza_un_riesgo_que_no_es_del_vocabulario(riesgo):
    rota = _respuesta_sana(risk_assessment={"risk": riesgo, "score": 50})

    assert any("risk=" in p for p in revisar_predict(200, rota))


@pytest.mark.parametrize("puntuacion", [-1, 101, "88", None, 88.5])
def test_rechaza_un_score_fuera_de_rango_o_del_tipo_que_no_es(puntuacion):
    rota = _respuesta_sana(risk_assessment={"risk": "LOW", "score": puntuacion})

    assert any("score=" in p for p in revisar_predict(200, rota))


@pytest.mark.parametrize("crudo", [b"", b"<html>502 Bad Gateway</html>", b"null", b"[1,2]"])
def test_un_cuerpo_que_no_es_json_de_objeto_no_revienta(crudo):
    """Un 502 de Render devuelve HTML, no JSON."""
    assert _json_o_vacio(crudo) == {}


def test_reintenta_los_estados_transitorios(monkeypatch):
    """503 es el semáforo ocupado y 502 el despliegue a medio rodar.

    Rendirse al primer intento haría fallar el smoke test por tráfico normal.
    """
    respuestas = [(503, {}), (502, {}), (200, _respuesta_sana())]
    monkeypatch.setattr("scripts.smoke_test.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "scripts.smoke_test._peticion", lambda *a, **k: respuestas.pop(0)
    )

    status, payload = analizar(
        "https://x", api_key="k", url="https://example.com", timeout_s=1
    )

    assert status == 200
    assert revisar_predict(status, payload) == []


def test_se_rinde_si_el_estado_transitorio_persiste(monkeypatch):
    """Reintentar para siempre convertiría un servicio caído en un job colgado."""
    monkeypatch.setattr("scripts.smoke_test.time.sleep", lambda _: None)
    monkeypatch.setattr("scripts.smoke_test._peticion", lambda *a, **k: (502, {}))

    status, _ = analizar(
        "https://x", api_key="k", url="https://example.com", timeout_s=1, reintentos=3
    )

    assert status == 502


def test_un_error_de_red_tambien_se_rinde(monkeypatch):
    """_peticion traduce un fallo de conexión a (None, {})."""
    monkeypatch.setattr("scripts.smoke_test.time.sleep", lambda _: None)
    monkeypatch.setattr("scripts.smoke_test._peticion", lambda *a, **k: (None, {}))

    status, payload = analizar(
        "https://x", api_key="k", url="https://example.com", timeout_s=1, reintentos=2
    )

    assert status is None
    assert revisar_predict(status, payload) != []
