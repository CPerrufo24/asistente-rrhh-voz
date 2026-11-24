from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.genai import types

from app import config


def _partes_texto(evento: Any) -> list[types.Part]:
    content = getattr(evento, "content", None)
    if not content or not content.parts:
        return []
    return list(content.parts)


def resumir_evento(evento: Any) -> list[dict[str, Any]]:
    resumen: list[dict[str, Any]] = []

    for llamada in getattr(evento, "get_function_calls", lambda: [])():
        resumen.append(
            {
                "tipo": "tool",
                "nombre": llamada.name,
                "args": llamada.args or {},
            }
        )

    for respuesta in getattr(evento, "get_function_responses", lambda: [])():
        fuentes: list[str] = []
        alerta_inyeccion = False
        payload = respuesta.response or {}
        if isinstance(payload, dict):
            resultados = payload.get("resultados")
            if isinstance(resultados, list):
                for resultado in resultados:
                    if not isinstance(resultado, dict):
                        continue
                    fuente = resultado.get("fuente")
                    if fuente is not None:
                        fuentes.append(str(fuente))
                    if resultado.get("alerta_inyeccion"):
                        alerta_inyeccion = True
            elif payload.get("folio") is not None:
                fuentes.append(str(payload["folio"]))

        item: dict[str, Any] = {
            "tipo": "tool_resultado",
            "nombre": respuesta.name,
            "fuentes": fuentes,
        }
        if alerta_inyeccion:
            item["alerta_inyeccion"] = True
        resumen.append(item)

    return resumen


def texto_final(eventos: list[Any]) -> str:
    fragmentos: list[str] = []
    for evento in eventos:
        if not getattr(evento, "is_final_response", lambda: False)():
            continue
        for parte in _partes_texto(evento):
            if parte.text:
                fragmentos.append(parte.text)
    return "".join(fragmentos)


def uso_tokens(eventos: list[Any]) -> dict[str, int]:
    entrada = 0
    salida = 0
    for evento in eventos:
        metadata = getattr(evento, "usage_metadata", None)
        if not metadata:
            continue
        entrada += int(getattr(metadata, "prompt_token_count", 0) or 0)
        salida += int(getattr(metadata, "candidates_token_count", 0) or 0)
    return {"entrada": entrada, "salida": salida}


def registrar(registro: dict[str, Any]) -> None:
    ruta = Path(config.RUTA_TRAZAS)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False))
        archivo.write("\n")
