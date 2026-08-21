"""Tests de la configuración de logging.

El fallo que arreglan: nadie llamaba a basicConfig, así que el root logger no
tenía handlers y todo lo que registraba el proyecto (middleware de requests,
circuit breaker de VirusTotal, semáforo de concurrencia) se descartaba en
silencio. Bajo uvicorn no se notaba porque uvicorn sí configura los suyos.
"""

import io
import logging
import os
import sys
from unittest.mock import patch

import pytest

from backend.app.core import logging_config


@pytest.fixture
def root_sin_handlers():
    """Deja el root logger vacío durante el test y lo restaura al salir.

    Se vacía aquí y no en el cuerpo de cada test porque el plugin de logging de
    pytest instala su LogCaptureHandler *después* del setup del fixture: hay que
    quitarlo ya empezada la fase de ejecución, no antes.

    Restaurar importa: `configure()` toca estado global (handlers y nivel del
    root, niveles de varias librerías) y sin deshacerlo los tests siguientes
    —y caplog— heredarían la configuración.
    """
    root = logging.getLogger()
    handlers_previos = root.handlers[:]
    nivel_previo = root.level
    niveles_previos = {
        nombre: logging.getLogger(nombre).level for nombre in logging_config._NOISY_LOGGERS
    }

    root.handlers = []
    try:
        yield root
    finally:
        for h in root.handlers:
            if h not in handlers_previos:
                h.close()
        root.handlers[:] = handlers_previos
        root.setLevel(nivel_previo)
        for nombre, nivel in niveles_previos.items():
            logging.getLogger(nombre).setLevel(nivel)


def test_configure_instala_un_handler_en_el_root(root_sin_handlers):
    """Sin esto, cada logger del proyecto propaga a la nada."""
    root_sin_handlers.handlers.clear()

    logging_config.configure()

    assert root_sin_handlers.handlers, "el root sigue sin handlers: los logs se pierden"


def test_los_loggers_del_proyecto_llegan_a_la_salida(root_sin_handlers):
    """Comprobación de extremo a extremo: el mensaje sale escrito."""
    root_sin_handlers.handlers.clear()
    logging_config.configure()

    salida = io.StringIO()
    root_sin_handlers.handlers[0].stream = salida
    logging.getLogger("phishing_api").info("POST /predict 200 42ms")

    assert "POST /predict 200 42ms" in salida.getvalue()


def test_no_duplica_handlers_si_ya_habia_logging_configurado(root_sin_handlers):
    """Bajo pytest o gunicorn el root ya viene con handler.

    Añadir el nuestro encima haría que cada línea saliera dos veces, que es
    peor que el problema original porque parece que funciona.
    """
    root_sin_handlers.handlers.clear()
    previo = logging.StreamHandler(io.StringIO())
    root_sin_handlers.addHandler(previo)

    logging_config.configure()

    assert root_sin_handlers.handlers == [previo]


def test_configure_es_idempotente(root_sin_handlers):
    root_sin_handlers.handlers.clear()
    logging_config.configure()
    cuantos = len(root_sin_handlers.handlers)

    logging_config.configure()

    assert len(root_sin_handlers.handlers) == cuantos


@pytest.mark.parametrize(
    "raw,esperado",
    [
        (None, logging.INFO),          # sin configurar
        ("DEBUG", logging.DEBUG),
        ("warning", logging.WARNING),  # minúsculas
        ("  ERROR  ", logging.ERROR),  # espacios de un copy/paste
        ("VERBOSE", logging.INFO),     # no existe
        ("", logging.INFO),            # vacío
        ("7", logging.INFO),           # numérico, no es un nombre de nivel
    ],
)
def test_nivel_desde_el_entorno(raw, esperado):
    """Una env var mal escrita no puede dejar el servicio sin logs."""
    env = {} if raw is None else {"LOG_LEVEL": raw}
    with patch.dict(os.environ, env, clear=False):
        if raw is None:
            os.environ.pop("LOG_LEVEL", None)
        assert logging_config._level_from_env() == esperado


def test_las_librerias_ruidosas_se_callan_en_info(root_sin_handlers):
    """A nivel INFO urllib3 y transformers tapan las líneas del proyecto."""
    root_sin_handlers.handlers.clear()

    with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=False):
        logging_config.configure()

    assert logging.getLogger("urllib3").level == logging.WARNING
    assert logging.getLogger("transformers").level == logging.WARNING


def test_en_debug_no_se_silencia_nada(root_sin_handlers):
    """Si alguien pide DEBUG es justo porque quiere ver ese ruido."""
    root_sin_handlers.handlers.clear()

    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False):
        logging_config.configure()

    assert logging.getLogger("urllib3").level != logging.WARNING


def test_un_caracter_no_representable_no_tumba_el_log(root_sin_handlers):
    """En Windows stdout sale en cp1252 y model_warmup registra un emoji.

    Sin el manejador de errores, el handler lanza UnicodeEncodeError y en vez
    de la línea aparece un traceback de "--- Logging error ---".
    """
    root_sin_handlers.handlers.clear()
    cp1252 = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    with patch.object(sys, "stdout", cp1252):
        logging_config.configure()
        logging.getLogger("phishing_api").info("⚠️ lazy loading")  # no debe lanzar


def test_un_stdout_sin_reconfigure_no_rompe_el_arranque(root_sin_handlers):
    """pytest y otros hosts sustituyen sys.stdout por objetos sin reconfigure."""
    root_sin_handlers.handlers.clear()

    with patch.object(sys, "stdout", io.StringIO()):
        logging_config.configure()  # no debe lanzar

    assert root_sin_handlers.handlers
