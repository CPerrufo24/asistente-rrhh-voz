"""Corre los casos de data/evaluacion/casos.md contra el agente real y reporta resultados.

Uso:
    uv run python scripts/evaluar.py              # todos los casos
    uv run python scripts/evaluar.py 3 11         # solo algunos
    MODELO_TEXTO=gemini-3.8-flash uv run python scripts/evaluar.py

Cada caso corre en una sesión nueva. Imprime tools usadas, fuentes, latencia, tokens y la
respuesta, y guarda el resultado en var/evaluacion-<modelo>.json.
"""

import asyncio
import json
import re
import sys
import time

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app import config, traza
from app.agent import crear_agente


def leer_casos() -> list[dict]:
    texto = (config.DIR_DATOS / "evaluacion" / "casos.md").read_text(encoding="utf-8")
    casos = []
    for linea in texto.splitlines():
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) == 5 and re.fullmatch(r"\d+", celdas[0]):
            num, pregunta, tipo, esperado, fuente = celdas
            casos.append({"n": int(num), "pregunta": pregunta, "tipo": tipo, "esperado": esperado})
    return casos


async def correr(caso: dict, runner: Runner, sesiones: InMemorySessionService) -> dict:
    sesion = await sesiones.create_session(app_name="evaluacion", user_id="evaluador")
    inicio = time.perf_counter()
    eventos = [
        e
        async for e in runner.run_async(
            user_id="evaluador",
            session_id=sesion.id,
            new_message=types.Content(role="user", parts=[types.Part(text=caso["pregunta"])]),
        )
    ]
    pasos = [p for e in eventos for p in traza.resumir_evento(e)]
    return {
        **caso,
        "respuesta": traza.texto_final(eventos),
        "tools": [p["nombre"] for p in pasos if p["tipo"] == "tool"],
        "fuentes": sorted({f for p in pasos for f in p.get("fuentes", [])}),
        "alerta_inyeccion": any(p.get("alerta_inyeccion") for p in pasos),
        "latencia_ms": int((time.perf_counter() - inicio) * 1000),
        "tokens": traza.uso_tokens(eventos),
    }


async def main(filtro: set[int]) -> None:
    sesiones = InMemorySessionService()
    runner = Runner(app_name="evaluacion", agent=crear_agente(), session_service=sesiones)
    resultados = []
    for caso in leer_casos():
        if filtro and caso["n"] not in filtro:
            continue
        r = await correr(caso, runner, sesiones)
        resultados.append(r)
        print(f"\n#{r['n']} [{r['tipo']}] {r['pregunta']}")
        print(f"  tools: {r['tools']}  fuentes: {r['fuentes']}  alerta: {r['alerta_inyeccion']}")
        print(f"  {r['latencia_ms']} ms, tokens {r['tokens']}")
        print(f"  → {r['respuesta']}")
        print(f"  esperado: {r['esperado']}")
    salida = config.RAIZ / "var" / f"evaluacion-{config.MODELO_TEXTO}.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    lat = sorted(r["latencia_ms"] for r in resultados)
    ent = sum(r["tokens"]["entrada"] for r in resultados) / len(resultados)
    sal = sum(r["tokens"]["salida"] for r in resultados) / len(resultados)
    print(f"\nModelo {config.MODELO_TEXTO}: {len(resultados)} casos")
    print(f"Latencia mediana {lat[len(lat) // 2]} ms, máxima {lat[-1]} ms")
    print(f"Tokens promedio por consulta: entrada {ent:.0f}, salida {sal:.0f}")
    print(f"Resultados en {salida}")


if __name__ == "__main__":
    asyncio.run(main({int(a) for a in sys.argv[1:]}))
