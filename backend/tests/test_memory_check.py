"""Tests de la lógica pura de `scripts/memory_check.py`.

El script necesita Docker para hacer su trabajo, pero las dos piezas que pueden
mentir en silencio —interpretar el RSS y decidir si hubo regresión— no lo
necesitan y son las que se prueban aquí.
"""

import pytest

from scripts.memory_check import mib_desde_stats, veredicto


@pytest.mark.parametrize(
    "linea,esperado",
    [
        ("395.3MiB / 512MiB", 395.3),
        ("874MiB / 2GiB", 874.0),
        ("1.2GiB / 2GiB", 1228.8),      # la unidad cambia sola al crecer
        ("512KiB / 512MiB", 0.5),
        ("948B / 512MiB", pytest.approx(0.000904, rel=1e-2)),
        ("  441.3MiB / 512MiB", 441.3),  # con espacio delante
    ],
)
def test_interpreta_el_memusage_de_docker(linea, esperado):
    """docker stats cambia de unidad según el tamaño.

    Compararlas como texto haría que "1GiB" pareciera menor que "900MiB", y el
    pico medido saldría más bajo que el real justo cuando importa.
    """
    assert mib_desde_stats(linea) == esperado


@pytest.mark.parametrize("linea", ["", None, "n/a", "-- / --", "MiB / 512MiB", "12XiB / 1GiB"])
def test_una_lectura_ilegible_no_se_cuela_como_cero(linea):
    """Devolver 0.0 haría que un contenedor muerto pareciera de bajo consumo."""
    assert mib_desde_stats(linea) is None


def test_sin_oom_y_con_respuesta_no_hay_problemas():
    assert veredicto(oom_killed=False, sigue_vivo=True, estados=[200, 200]) == []


def test_detecta_el_oom():
    """La regresión que vigila el script."""
    problemas = veredicto(oom_killed=True, sigue_vivo=False, estados=[None, None])

    assert any("OOM" in p for p in problemas)


def test_un_contenedor_muerto_falla_aunque_docker_no_marque_oom():
    """El worker puede morir sin que el flag de OOM quede puesto.

    Con `WEB_CONCURRENCY=1` matar al worker tumba el servicio igual, así que el
    criterio es que el contenedor siga en pie, no cómo lo mataron.
    """
    problemas = veredicto(oom_killed=False, sigue_vivo=False, estados=[200])

    assert problemas


def test_un_503_no_es_un_fallo_de_memoria():
    """Es el semáforo rindiéndose en orden: exactamente lo que debe pasar.

    Marcarlo como fallo penalizaría el comportamiento que evita el OOM.
    """
    assert veredicto(oom_killed=False, sigue_vivo=True, estados=[200, 503, 503]) == []


def test_si_ninguna_peticion_llego_a_200_es_un_fallo():
    """Sobrevivir sin servir nada no es aprobar.

    Un contenedor vivo que devuelve 503 a todo cabría en memoria pero no
    estaría analizando nada.
    """
    problemas = veredicto(oom_killed=False, sigue_vivo=True, estados=[503, 503])

    assert problemas
