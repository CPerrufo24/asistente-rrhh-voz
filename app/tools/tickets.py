"""Escalamiento a RRHH: crea tickets en SQLite."""


def crear_ticket_rrhh(
    asunto: str, descripcion: str, categoria: str = "general", numero_empleado: str = ""
) -> dict:
    """Crea un ticket para que una persona de RRHH atienda el caso.

    Usar cuando la respuesta no está en el reglamento ni en la LFT, cuando el caso
    requiere criterio humano (quejas, acoso, excepciones) o cuando el empleado lo pide.

    Args:
        asunto: resumen corto del caso.
        descripcion: detalle de lo que pidió el empleado y lo que ya se le respondió.
        categoria: vacaciones, nomina, permisos, prestaciones, conducta o general.
        numero_empleado: número de empleado si se conoce.

    Returns:
        dict con folio, estado y tiempo_respuesta_estimado.
    """
    raise NotImplementedError
