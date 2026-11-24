"""Cálculo de días de vacaciones según el artículo 76 de la LFT (reforma 2023)."""

from __future__ import annotations

from datetime import date

_PRIMA_VACACIONAL = (
    "50 % del salario de los días de vacaciones (reglamento interno; "
    "la LFT, art. 80, exige al menos 25 %)"
)
_FUNDAMENTO = [
    "LFT, artículo 76",
    "LFT, artículo 80",
    "Reglamento interno (días extra y prima)",
]
_NOTA_SIN_ANIO = "aún no cumple un año; el derecho nace al cumplirlo (art. 76 LFT)"


def _dias_por_ley(antiguedad_anios: int) -> int:
    if antiguedad_anios < 1:
        return 0
    if antiguedad_anios <= 5:
        return 10 + 2 * antiguedad_anios
    return 20 + 2 * (1 + (antiguedad_anios - 6) // 5)


def _parsear_fecha(valor: str) -> date | None:
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def calcular_vacaciones(
    fecha_ingreso: str, dias_tomados: int = 0, fecha_referencia: str | None = None
) -> dict:
    """Calcula los días de vacaciones que corresponden por ley y los que quedan.

    Args:
        fecha_ingreso: fecha de ingreso en formato AAAA-MM-DD.
        dias_tomados: días ya disfrutados en el periodo actual.
        fecha_referencia: fecha de cálculo AAAA-MM-DD (por defecto, hoy).

    Returns:
        dict con antiguedad, dias_por_ley, dias_disponibles, prima_vacacional y fundamento.
    """
    ingreso = _parsear_fecha(fecha_ingreso)
    if ingreso is None:
        return {"error": f"Fecha de ingreso inválida: {fecha_ingreso!r}."}

    if fecha_referencia is None:
        referencia = date.today()
    else:
        referencia = _parsear_fecha(fecha_referencia)
        if referencia is None:
            return {"error": f"Fecha de referencia inválida: {fecha_referencia!r}."}

    if ingreso > referencia or ingreso > date.today():
        return {"error": "La fecha de ingreso no puede ser futura."}

    antiguedad_anios = referencia.year - ingreso.year
    if (referencia.month, referencia.day) < (ingreso.month, ingreso.day):
        antiguedad_anios -= 1

    dias_por_ley = _dias_por_ley(antiguedad_anios)
    dias_extra_reglamento = 2 if antiguedad_anios >= 5 else 0
    dias_totales = dias_por_ley + dias_extra_reglamento
    try:
        tomados = int(dias_tomados)
    except (TypeError, ValueError):
        return {"error": "Los días tomados deben ser un número entero."}

    resultado = {
        "antiguedad_anios": antiguedad_anios,
        "dias_por_ley": dias_por_ley,
        "dias_extra_reglamento": dias_extra_reglamento,
        "dias_totales": dias_totales,
        "dias_disponibles": max(0, dias_totales - tomados),
        "prima_vacacional": _PRIMA_VACACIONAL,
        "fundamento": list(_FUNDAMENTO),
    }
    if antiguedad_anios < 1:
        resultado["nota"] = _NOTA_SIN_ANIO
    return resultado
