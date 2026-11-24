"""Cálculo de días de vacaciones según el artículo 76 de la LFT (reforma 2023)."""


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
    raise NotImplementedError
