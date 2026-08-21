#!/usr/bin/env python3
"""Comprueba que /predict no se sale del presupuesto de RAM de Render.

Reproduce la restricción real en local: la imagen de producción dentro de un
contenedor capado a 512 MB, con `ENVIRONMENT=production` (carga perezosa en la
primera petición, como en Render) y un solo worker.

Es la herramienta que encontró el fallo de fondo del 502. Medido el 2026-08-21:

    | /predict en paralelo | Pico RSS | Resultado          |
    |----------------------|----------|--------------------|
    | 1                    |  395 MiB | 200 OK             |
    | 2                    |  441 MiB | OOM, worker muerto |
    | 6                    |  500 MiB | OOM, worker muerto |
    | 6, con 2 GB          |  874 MiB | 200 OK             |
    | 6, con el semáforo   |  487 MiB | 200 OK, 0 rechazos |

Una petición cabía de sobra; el problema era la concurrencia. Y pasarse no
degrada: el kernel mata al worker único y con él se cae /health, así que el
servicio entero desaparece hasta que Render lo reinicia.

Uso:

    python scripts/memory_check.py                  # build + 2 concurrentes
    python scripts/memory_check.py --concurrency 6
    python scripts/memory_check.py --no-build       # reutiliza la imagen
    python scripts/memory_check.py --memory 2g      # comprobar el margen con más RAM

Sale con 0 si el contenedor sobrevive y sirve el análisis, y con 1 si el kernel
lo mata — que es la regresión a vigilar. No está en CI: el build descarga ~821 MB
de pesos desde Hugging Face, demasiado para un job por PR.
"""

import argparse
import json
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

IMAGEN = "phishing-ia:memcheck"
CONTENEDOR = "phishing-ia-memcheck"
# Solo sirve para arrancar en ENVIRONMENT=production, que exige API_KEY.
CLAVE = "memcheck-local-key"

_UNIDADES = {"B": 1 / 1024**2, "KIB": 1 / 1024, "MIB": 1.0, "GIB": 1024.0}


def _docker(*args, capturar=True, check=False):
    return subprocess.run(
        ["docker", *args],
        capture_output=capturar,
        text=True,
        check=check,
    )


def mib_desde_stats(linea):
    """Convierte el `MemUsage` de `docker stats` a MiB. None si no se entiende.

    El formato es "123.4MiB / 512MiB" y la unidad cambia sola según el tamaño,
    así que compararlas como texto daría que 1GiB < 900MiB.
    """
    if not linea:
        return None
    m = re.match(r"\s*([\d.]+)\s*([A-Za-z]+)", linea)
    if not m:
        return None
    factor = _UNIDADES.get(m.group(2).upper())
    if factor is None:
        return None
    try:
        return float(m.group(1)) * factor
    except ValueError:
        return None


def veredicto(*, oom_killed, sigue_vivo, estados):
    """Problemas encontrados; lista vacía = la memoria aguantó.

    Función pura para poder probarla sin Docker. Un 503 no es un fallo: es el
    semáforo rindiéndose ordenadamente, que es justo lo que debe pasar cuando
    hay más demanda que memoria. Lo que no puede pasar es que muera el worker.
    """
    problemas = []
    if oom_killed:
        problemas.append("el kernel mató al contenedor por OOM")
    if not sigue_vivo:
        problemas.append("el contenedor no sobrevivió a las peticiones")
    if not any(e == 200 for e in estados):
        problemas.append(f"ninguna petición devolvió 200 (estados: {estados})")
    return problemas


class _Muestreador(threading.Thread):
    """Sondea el RSS del contenedor mientras corren las peticiones.

    `docker stats --no-stream` es una foto, así que el pico solo se ve
    muestreando: la carga de los modelos dura unos segundos y es donde está.
    """

    def __init__(self, contenedor, intervalo=0.2):
        super().__init__(daemon=True)
        self.contenedor = contenedor
        self.intervalo = intervalo
        self.pico_mib = 0.0
        self._parar = threading.Event()

    def run(self):
        while not self._parar.is_set():
            res = _docker("stats", "--no-stream", "--format", "{{.MemUsage}}", self.contenedor)
            mib = mib_desde_stats(res.stdout) if res.returncode == 0 else None
            if mib is not None:
                self.pico_mib = max(self.pico_mib, mib)
            self._parar.wait(self.intervalo)

    def parar(self):
        self._parar.set()
        self.join(timeout=10)


def _predict(puerto, url, timeout):
    peticion = urllib.request.Request(
        f"http://localhost:{puerto}/predict",
        data=json.dumps({"url": url}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": CLAVE},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _esperar_health(puerto, limite_s=120):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        try:
            with urllib.request.urlopen(
                f"http://localhost:{puerto}/health", timeout=3
            ) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=2,
                        help="peticiones simultáneas a /predict "
                             "(2 era el mínimo que provocaba el OOM)")
    parser.add_argument("--memory", default="512m", help="límite del contenedor")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--url", default="https://example.com", help="URL a analizar")
    parser.add_argument("--timeout", type=int, default=240,
                        help="segundos por petición (la primera carga los modelos)")
    parser.add_argument("--no-build", action="store_true",
                        help=f"reutiliza la imagen {IMAGEN} en vez de reconstruirla")
    args = parser.parse_args(argv)

    if _docker("version").returncode != 0:
        print("FALLO: no hay un demonio de Docker accesible (¿Docker Desktop arrancado?)")
        return 1

    if not args.no_build:
        print(f"Construyendo {IMAGEN} (la primera vez descarga ~821 MB de pesos)...")
        # Contexto = raíz del repo, como espera backend/Dockerfile.
        if _docker("build", "-f", "backend/Dockerfile", "-t", IMAGEN, ".",
                   capturar=False).returncode != 0:
            print("FALLO: no se pudo construir la imagen.")
            return 1

    _docker("rm", "-f", CONTENEDOR)

    print(f"Arrancando con límite de {args.memory}...")
    arrancado = _docker(
        "run", "-d", "--name", CONTENEDOR,
        # --memory-swap igual a --memory desactiva el swap: sin esto el
        # contenedor se desborda a disco y nunca reproduce el OOM de Render.
        "-m", args.memory, "--memory-swap", args.memory,
        "-e", "ENVIRONMENT=production",
        "-e", f"API_KEY={CLAVE}",
        "-e", "PORT=8000",
        "-p", f"{args.port}:8000",
        IMAGEN,
    )
    if arrancado.returncode != 0:
        print(f"FALLO al arrancar el contenedor: {arrancado.stderr.strip()}")
        return 1

    try:
        if not _esperar_health(args.port):
            print("FALLO: /health no respondió; el contenedor no llegó a arrancar.")
            print(_docker("logs", "--tail", "30", CONTENEDOR).stdout)
            return 1

        reposo = mib_desde_stats(
            _docker("stats", "--no-stream", "--format", "{{.MemUsage}}", CONTENEDOR).stdout
        )
        print(f"RSS en reposo (modelos aún sin cargar): {reposo:.1f} MiB")

        muestreador = _Muestreador(CONTENEDOR)
        muestreador.start()

        print(f"Lanzando {args.concurrency} peticiones simultáneas a /predict...")
        inicio = time.monotonic()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            estados = list(pool.map(
                lambda _: _predict(args.port, args.url, args.timeout),
                range(args.concurrency),
            ))
        transcurrido = time.monotonic() - inicio
        muestreador.parar()

        oom = _docker("inspect", "-f", "{{.State.OOMKilled}}", CONTENEDOR).stdout.strip() == "true"
        vivo = _docker("inspect", "-f", "{{.State.Running}}", CONTENEDOR).stdout.strip() == "true"

        print(f"\nEstados: {estados}  ({transcurrido:.1f}s)")
        print(f"Pico de RSS: {muestreador.pico_mib:.1f} MiB de {args.memory}")
        print(f"OOMKilled={oom} Running={vivo}")

        problemas = veredicto(oom_killed=oom, sigue_vivo=vivo, estados=estados)
        if problemas:
            print("\nFALLO: no cabe en el presupuesto de memoria.")
            for p in problemas:
                print(f"  - {p}")
            print("\nÚltimas líneas del log:")
            print(_docker("logs", "--tail", "30", CONTENEDOR).stdout)
            return 1

        rechazos = sum(1 for e in estados if e == 503)
        print(f"\nOK: el servicio sobrevivió a {args.concurrency} análisis simultáneos"
              f" ({rechazos} encolados hasta rendirse con 503).")
        return 0
    finally:
        _docker("rm", "-f", CONTENEDOR)


if __name__ == "__main__":
    sys.exit(main())
