"""Consulta del directorio ficticio de empleados."""

from __future__ import annotations

import csv
import re

from app import config


def _normalizar_numero(numero_empleado: str) -> str:
    limpio = re.sub(r"[^0-9A-Za-z]", "", str(numero_empleado or "")).upper()
    if limpio.startswith("E") and limpio[1:].isdigit():
        limpio = limpio[1:]
    limpio = limpio.lstrip("0")
    return limpio or "0"


def consultar_empleado(numero_empleado: str) -> dict:
    """Devuelve los datos laborales de un empleado por su número (por ejemplo "E-1001").

    Args:
        numero_empleado: número de empleado.

    Returns:
        dict con nombre, puesto, fecha_ingreso y dias_vacaciones_tomados, o "error".
    """
    buscado = _normalizar_numero(numero_empleado)
    ruta = config.DIR_DATOS / "empleados.csv"
    if ruta.is_file():
        with ruta.open(encoding="utf-8-sig", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                if _normalizar_numero(fila.get("numero_empleado", "")) == buscado:
                    resultado = dict(fila)
                    try:
                        resultado["dias_vacaciones_tomados"] = int(
                            resultado.get("dias_vacaciones_tomados") or 0
                        )
                    except (TypeError, ValueError):
                        resultado["dias_vacaciones_tomados"] = 0
                    return resultado
    return {"error": f"No existe el empleado {numero_empleado}"}
