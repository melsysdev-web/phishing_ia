"""Configuración de logging del backend.

Hasta ahora ningún módulo llamaba a `basicConfig` ni añadía un handler, así que
`logging.getLogger("phishing_api")` propagaba a un root sin handlers y **todo lo
que escribía se perdía**. Bajo uvicorn el fallo pasa desapercibido: uvicorn sí
configura sus propios loggers (`uvicorn`, `uvicorn.access`, `uvicorn.error`) y
esos aparecen en la consola, lo que da la impresión de que el logging funciona.

Lo que llevaba tiempo escribiendo al vacío en producción:

- `RequestLoggingMiddleware` (latencia por request)
- el circuit breaker de cuota de VirusTotal (`quota_circuit.py`)
- el semáforo de concurrencia (`concurrency.py`), incluida su línea de arranque
- el warmup de modelos (`model_warmup.py`)

Justo los cuatro sitios donde se mira cuando el servicio se porta raro.

`LOG_LEVEL` ajusta el nivel sin tocar código (default `INFO`).
"""

import logging
import os
import sys

_DEFAULT_LEVEL = "INFO"

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# A nivel INFO estas librerías tapan las líneas del proyecto: urllib3 registra
# cada conexión, transformers y huggingface_hub narran la carga de cada modelo.
_NOISY_LOGGERS = (
    "asyncio",
    "filelock",
    "httpcore",
    "httpx",
    "huggingface_hub",
    "transformers",
    "urllib3",
)


def _level_from_env() -> int:
    """Traduce `LOG_LEVEL` a un nivel de logging; un valor inválido cae a INFO.

    Una env var mal escrita no puede dejar el servicio sin logs — que es
    exactamente el fallo que este módulo viene a arreglar.
    """
    mapping = logging.getLevelNamesMapping()
    raw = os.getenv("LOG_LEVEL", _DEFAULT_LEVEL).strip().upper()
    if raw not in mapping:
        # Todavía no hay logging configurado: el aviso va a stderr a mano.
        print(
            f"LOG_LEVEL={raw!r} no es un nivel válido; se usa {_DEFAULT_LEVEL}",
            file=sys.stderr,
        )
        return mapping[_DEFAULT_LEVEL]
    return mapping[raw]


def _make_stdout_unencodable_safe() -> None:
    """Evita que un carácter no representable tumbe el log.

    En Windows `sys.stdout` sale en cp1252, y `model_warmup.py` registra un
    emoji: el handler revienta con UnicodeEncodeError y en vez de la línea
    aparece un "--- Logging error ---" con su traceback. En Linux (Render) no
    pasa porque el default es UTF-8, así que es un fallo que solo se ve en
    desarrollo — el peor sitio para perder precisamente los logs de arranque.

    Solo se cambia el manejador de errores, no la codificación: reemplazar la
    codificación cambiaría cómo se ve todo lo demás que escribe a esa consola.
    Se reconfigura el propio `sys.stdout` en vez de envolverlo en otro
    TextIOWrapper para no acabar con dos búferes sobre el mismo descriptor
    (uvicorn escribe ahí también, y se entrelazarían).
    """
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError, OSError):
        # stdout puede estar sustituido (captura de pytest) o cerrado.
        pass


def configure() -> None:
    """Instala un handler en el root logger. Idempotente.

    Si el root ya tiene handlers no toca nada: bajo pytest los pone el plugin de
    logging (`caplog`) y bajo otro host podría ponerlos el propio host. Añadir
    uno encima duplicaría cada línea en vez de arreglar nada.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    _make_stdout_unencodable_safe()
    level = _level_from_env()
    logging.basicConfig(
        level=level,
        format=_FORMAT,
        datefmt=_DATEFMT,
        # stdout, no stderr: en Render (y en `docker logs`) ambos se recogen,
        # pero mezclar logs de aplicación con stderr hace que cualquier
        # filtro por flujo confunda actividad normal con errores.
        stream=sys.stdout,
    )

    if level > logging.DEBUG:
        # En DEBUG el ruido se quiere: es cuando hace falta ver los reintentos
        # de urllib3 o la carga de un modelo.
        for name in _NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
