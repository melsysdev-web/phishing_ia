"""Tests de la guarda de arranque que impide una producción sin autenticación.

El backend estuvo desplegado con `/predict` y `/analyze-content` abiertos a
cualquiera, y nada lo dijo. La guarda existe para que ese estado sea imposible
por descuido — pero posible a propósito, porque la extensión se publica en una
tienda y un paquete descargable no puede llevar un secreto de verdad.
"""

import logging

import pytest

from backend.app.main import verify_auth_config


class _Config:
    """Doble de `settings` con solo los tres campos que mira la guarda."""

    def __init__(self, environment="development", api_key="", allow_unauthenticated=False):
        self.environment = environment
        self.api_key = api_key
        self.allow_unauthenticated = allow_unauthenticated


def test_produccion_sin_clave_y_sin_declararlo_no_arranca():
    """El descuido que la guarda existe para atrapar."""
    with pytest.raises(RuntimeError, match="ALLOW_UNAUTHENTICATED"):
        verify_auth_config(_Config(environment="production", api_key=""))


def test_produccion_con_clave_arranca():
    verify_auth_config(_Config(environment="production", api_key="una-clave"))


def test_produccion_sin_clave_pero_declarada_arranca(caplog):
    """La exposición pública deliberada se permite, pero deja rastro.

    Sin el aviso, una API abierta a propósito y una abierta por error se leen
    igual en los logs, y la guarda dejaría de servir para nada.
    """
    with caplog.at_level(logging.WARNING, logger="phishing_api"):
        verify_auth_config(
            _Config(environment="production", api_key="", allow_unauthenticated=True)
        )

    assert any(
        "sin autenticar" in r.message and r.levelno == logging.WARNING
        for r in caplog.records
    )


def test_en_desarrollo_no_se_exige_nada():
    """Pedir una clave en local solo estorbaría."""
    verify_auth_config(_Config(environment="development", api_key=""))


def test_la_declaracion_no_hace_falta_si_hay_clave(caplog):
    """Con clave puesta, ALLOW_UNAUTHENTICATED es irrelevante y no debe avisar.

    Avisar aquí entrenaría a ignorar el aviso, que es lo único que distingue una
    API pública a propósito de una por error.
    """
    with caplog.at_level(logging.WARNING, logger="phishing_api"):
        verify_auth_config(
            _Config(environment="production", api_key="k", allow_unauthenticated=True)
        )

    assert not caplog.records


@pytest.mark.parametrize("valor", ["1", "true", "TRUE", "True", "yes", "si", "sí"])
def test_valores_que_activan_la_declaracion(valor, monkeypatch):
    """Se escribe a mano en un dashboard: conviene aceptar las formas obvias."""
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", valor)
    import importlib

    from backend.app.core import config

    recargado = importlib.reload(config)
    try:
        assert recargado.settings.allow_unauthenticated is True
    finally:
        # config.settings es un singleton compartido: dejarlo recargado con la
        # env var puesta filtraría a los demás tests.
        monkeypatch.delenv("ALLOW_UNAUTHENTICATED")
        importlib.reload(config)


@pytest.mark.parametrize("valor", ["", "0", "false", "no", "quizá", "  "])
def test_valores_que_no_activan_la_declaracion(valor, monkeypatch):
    """Cualquier cosa que no sea un sí explícito deja la guarda en pie.

    Es lo seguro: un valor raro debe impedir el arranque, no abrir la API.
    """
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", valor)
    import importlib

    from backend.app.core import config

    recargado = importlib.reload(config)
    try:
        assert recargado.settings.allow_unauthenticated is False
    finally:
        monkeypatch.delenv("ALLOW_UNAUTHENTICATED")
        importlib.reload(config)
