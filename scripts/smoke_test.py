#!/usr/bin/env python3
"""Smoke test post-despliegue: comprueba que el backend *sirve predicciones*.

El agujero que tapa: el servicio estuvo desplegado devolviendo 502 en /predict
mientras /health y /metadata seguían en verde, y nadie se enteró. Ninguno de los
dos prueba nada útil —`/metadata` solo hace `.exists()` sobre los ficheros de
modelo, no dice si la inferencia cabe en memoria—, así que verificar un
despliegue exige llamar a /predict de verdad.

Uso:

    python scripts/smoke_test.py --base-url https://phishing-ia-smmy.onrender.com

La API key sale de --api-key o de SMOKE_API_KEY. Solo usa la librería estándar
para que en CI el job no tenga que instalar torch para hacer una petición HTTP.

Sale con 0 si el backend responde un análisis completo, y con 1 describiendo
qué falló si no.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

# example.com está reservado por la IANA: estable, benigno y sin dueño al que
# molestar. Además la respuesta queda cacheada, así que repetir el smoke test
# no quema cuota de VirusTotal.
URL_ANALIZADA = "https://example.com"

_RIESGOS_VALIDOS = {"LOW", "MEDIUM", "HIGH"}


def _peticion(url, *, metodo="GET", cuerpo=None, api_key=None, timeout=30):
    """Devuelve (status, payload). Un fallo de red se traduce a (None, {}).

    Los 4xx/5xx no son excepciones aquí: el status *es* el resultado que
    interesa comprobar.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    cabeceras = {"Accept": "application/json"}
    if datos is not None:
        cabeceras["Content-Type"] = "application/json"
    if api_key:
        cabeceras["X-API-Key"] = api_key

    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as resp:
            return resp.status, _json_o_vacio(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _json_o_vacio(e.read())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"    (sin respuesta: {e})")
        return None, {}


def _json_o_vacio(crudo):
    try:
        valor = json.loads(crudo)
    except (ValueError, TypeError):
        return {}
    return valor if isinstance(valor, dict) else {}


def revisar_predict(status, payload):
    """Lista de problemas encontrados en una respuesta de /predict; vacía = bien.

    Función pura para poder probarla sin red. Mira más allá del status porque
    el pipeline se degrada con elegancia: si ningún modelo carga, cada
    sub-servicio devuelve {"error": ...} y la respuesta sigue siendo un 200
    perfectamente formado. Eso es justo el fallo silencioso que se busca.
    """
    if status != 200:
        return [f"/predict respondió {status}, se esperaba 200"]

    problemas = []

    evaluacion = payload.get("risk_assessment")
    if not isinstance(evaluacion, dict):
        return ["la respuesta no trae risk_assessment"]

    riesgo = evaluacion.get("risk")
    if riesgo not in _RIESGOS_VALIDOS:
        problemas.append(f"risk={riesgo!r}, se esperaba uno de {sorted(_RIESGOS_VALIDOS)}")

    puntuacion = evaluacion.get("score")
    if not isinstance(puntuacion, int) or not 0 <= puntuacion <= 100:
        problemas.append(f"score={puntuacion!r}, se esperaba un entero entre 0 y 100")

    fusion = payload.get("machine_learning", {}).get("fusion", {})
    if not isinstance(fusion, dict) or "error" in fusion:
        # Los modelos no cargaron: el síntoma de un despliegue sin pesos o sin
        # memoria para cargarlos, invisible desde el status HTTP.
        detalle = fusion.get("error") if isinstance(fusion, dict) else fusion
        problemas.append(f"ningún modelo ML produjo predicción: {detalle}")
    elif "phishing_probability" not in fusion:
        problemas.append("la fusión no trae phishing_probability")

    return problemas


def esperar_a_que_responda(base_url, *, limite_s, espera_s=10):
    """Sondea /health hasta que conteste. Devuelve True si llegó a responder.

    Hace falta porque el arranque en frío de Render tarda 60-90 s y el job de
    CI se lanza en cuanto se hace merge, antes de que el despliegue ruede.
    """
    fin = time.monotonic() + limite_s
    intento = 0
    while time.monotonic() < fin:
        intento += 1
        restante = int(fin - time.monotonic())
        print(f"[health] intento {intento} (quedan {restante}s)...")
        status, _ = _peticion(f"{base_url}/health", timeout=15)
        if status == 200:
            print("[health] OK")
            return True
        print(f"    status={status}")
        time.sleep(espera_s)
    return False


def analizar(base_url, *, api_key, url, timeout_s, reintentos=3):
    """Llama a /predict, reintentando los estados transitorios.

    503 es el semáforo de concurrencia con todos los turnos ocupados y 502/504
    puede ser el despliegue a medio rodar; ninguno de los dos merece un fallo
    al primer intento, pero sí si persiste.
    """
    status, payload = None, {}
    for intento in range(1, reintentos + 1):
        print(f"[predict] intento {intento}/{reintentos} sobre {url}...")
        inicio = time.monotonic()
        status, payload = _peticion(
            f"{base_url}/predict",
            metodo="POST",
            cuerpo={"url": url},
            api_key=api_key,
            timeout=timeout_s,
        )
        transcurrido = time.monotonic() - inicio
        print(f"    status={status} en {transcurrido:.1f}s")

        if status not in (None, 502, 503, 504):
            return status, payload
        if intento < reintentos:
            time.sleep(15)

    return status, payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("SMOKE_BASE_URL", ""),
        help="URL del backend (o SMOKE_BASE_URL)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("SMOKE_API_KEY", ""),
        help="X-API-Key del backend (o SMOKE_API_KEY)",
    )
    parser.add_argument("--url", default=URL_ANALIZADA, help="URL a analizar")
    parser.add_argument(
        "--wait", type=int, default=300, help="segundos esperando a que /health responda"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=150,
        help="segundos por petición a /predict (la primera carga los modelos)",
    )
    args = parser.parse_args(argv)

    if not args.base_url:
        parser.error("hace falta --base-url o SMOKE_BASE_URL")
    base_url = args.base_url.rstrip("/")

    print(f"Smoke test contra {base_url}")

    if not esperar_a_que_responda(base_url, limite_s=args.wait):
        print(f"\nFALLO: /health no respondió en {args.wait}s. El servicio no está arriba.")
        return 1

    status, metadatos = _peticion(f"{base_url}/metadata", timeout=15)
    if status == 200:
        # Informativo, no un criterio: que los ficheros existan en disco no
        # implica que la inferencia funcione. Eso lo decide /predict.
        print(f"[metadata] version={metadatos.get('api_version')} models={metadatos.get('models')}")

    status, payload = analizar(
        base_url, api_key=args.api_key, url=args.url, timeout_s=args.timeout
    )

    problemas = revisar_predict(status, payload)
    if problemas:
        print("\nFALLO: el backend no está sirviendo análisis.")
        for p in problemas:
            print(f"  - {p}")
        if payload:
            print(f"\nRespuesta: {json.dumps(payload, ensure_ascii=False)[:800]}")
        return 1

    evaluacion = payload["risk_assessment"]
    print(f"\nOK: risk={evaluacion['risk']} score={evaluacion['score']}")
    if payload.get("cached"):
        # Tras un despliegue el cache en memoria arranca vacío, así que esto no
        # debería pasar; si pasa, el análisis lo sirvió una entrada previa y la
        # inferencia no llegó a ejercitarse.
        print("AVISO: la respuesta venía del cache; no se ejercitó la inferencia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
