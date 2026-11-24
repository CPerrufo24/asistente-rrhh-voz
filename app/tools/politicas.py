"""Búsqueda en el reglamento interno y la LFT (RAG léxico)."""


def buscar_politica(consulta: str, max_resultados: int = 4) -> dict:
    """Busca en el reglamento interno de la empresa y en la Ley Federal del Trabajo.

    Args:
        consulta: la pregunta o palabras clave del empleado.
        max_resultados: cuántos fragmentos devolver (1 a 8).

    Returns:
        dict con "resultados": lista de fragmentos con "fuente", "texto" y "puntaje".
    """
    raise NotImplementedError
