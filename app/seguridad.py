"""Detección y neutralización de instrucciones inyectadas en documentos."""

from __future__ import annotations

import re

TEXTO_OMITIDO = "[texto omitido: posible instrucción inyectada en el documento]"

PATRONES_INYECCION = [
    re.compile(
        r"ignora\s+(?:todas?\s+)?(?:tus|las|mis)\s+instrucciones(?:\s+anteriores)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"olvida\s+(?:todas?\s+)?(?:tus|las|mis)\s+(?:reglas|instrucciones)",
        re.IGNORECASE,
    ),
    re.compile(r"prompt\s+de\s+sistema", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"nota\s+para\s+el\s+asistente", re.IGNORECASE),
    re.compile(r"eres\s+ahora", re.IGNORECASE),
    re.compile(r"act[uú]a\s+como", re.IGNORECASE),
    re.compile(r"revela", re.IGNORECASE),
    re.compile(r"nuevas\s+instrucciones", re.IGNORECASE),
]


def detectar_inyeccion(texto: str) -> list[str]:
    """Devuelve los fragmentos del texto que coinciden con patrones de inyección."""
    if not texto:
        return []
    encontrados: list[tuple[int, str]] = []
    vistos: set[tuple[int, int]] = set()
    for patron in PATRONES_INYECCION:
        for coincidencia in patron.finditer(texto):
            inicio, fin = coincidencia.span()
            if (inicio, fin) in vistos:
                continue
            vistos.add((inicio, fin))
            encontrados.append((inicio, texto[inicio:fin]))
    encontrados.sort(key=lambda item: item[0])
    return [fragmento for _, fragmento in encontrados]


def _neutralizar_parrafo(parrafo: str) -> tuple[str, bool]:
    if not detectar_inyeccion(parrafo):
        return parrafo, False

    oraciones = re.split(r"(?<=[.!?])\s+", parrafo)
    nuevas: list[str] = []
    hubo_reemplazo = False
    for oracion in oraciones:
        if detectar_inyeccion(oracion):
            nuevas.append(TEXTO_OMITIDO)
            hubo_reemplazo = True
        else:
            nuevas.append(oracion)

    if hubo_reemplazo:
        return " ".join(nuevas), True
    return TEXTO_OMITIDO, True


def neutralizar(texto: str) -> tuple[str, bool]:
    """Reemplaza las oraciones o párrafos con posibles inyecciones."""
    if not texto:
        return texto, False

    partes = re.split(r"(\n\s*\n)", texto)
    salida: list[str] = []
    hubo = False
    for indice, parte in enumerate(partes):
        if indice % 2 == 1 or not parte:
            salida.append(parte)
            continue
        neutralizado, reemplazado = _neutralizar_parrafo(parte)
        salida.append(neutralizado)
        hubo = hubo or reemplazado
    return "".join(salida), hubo
