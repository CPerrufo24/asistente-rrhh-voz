from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from app import config, traza
from app.agent import crear_agente

APP_NAME = "asistente_rrhh"
USER_ID = "empleado"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

session_service = InMemorySessionService()
runner_texto = Runner(
    app_name=APP_NAME,
    agent=crear_agente(config.MODELO_TEXTO),
    session_service=session_service,
)
runner_voz = Runner(
    app_name=APP_NAME,
    agent=crear_agente(config.MODELO_VOZ),
    session_service=session_service,
)

app = FastAPI(title="Asistente de RRHH")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class MensajeChat(BaseModel):
    session_id: str = Field(min_length=1)
    mensaje: str = Field(max_length=2000)


async def _obtener_sesion(session_id: str, crear: bool = False):
    sesion = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    if sesion is None and crear:
        sesion = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
    return sesion


def _fuentes_unicas(items: list[dict[str, object]]) -> list[str]:
    fuentes: list[str] = []
    for item in items:
        if item.get("tipo") != "tool_resultado":
            continue
        for fuente in item.get("fuentes", []):
            if fuente not in fuentes:
                fuentes.append(fuente)
    return fuentes


@app.get("/api/salud")
async def salud() -> dict[str, object]:
    return {
        "ok": True,
        "modelo_texto": config.MODELO_TEXTO,
        "modelo_voz": config.MODELO_VOZ,
    }


@app.post("/api/sesiones")
async def crear_sesion() -> dict[str, str]:
    sesion = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    return {"session_id": sesion.id}


@app.post("/api/chat")
async def chat(payload: MensajeChat) -> dict[str, object]:
    if not payload.mensaje.strip():
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío.")

    sesion = await _obtener_sesion(payload.session_id)
    if sesion is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    inicio = time.perf_counter()
    eventos: list[object] = []
    try:
        async for evento in runner_texto.run_async(
            user_id=USER_ID,
            session_id=payload.session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=payload.mensaje)],
            ),
        ):
            eventos.append(evento)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - fallback
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    traza_eventos = [item for evento in eventos for item in traza.resumir_evento(evento)]
    respuesta = traza.texto_final(eventos)
    tokens = traza.uso_tokens(eventos)
    fuentes = _fuentes_unicas(traza_eventos)
    latencia_ms = int((time.perf_counter() - inicio) * 1000)

    traza.registrar(
        {
            "tipo": "chat",
            "session_id": payload.session_id,
            "mensaje": payload.mensaje,
            "respuesta": respuesta,
            "traza": traza_eventos,
            "fuentes": fuentes,
            "latencia_ms": latencia_ms,
            "tokens": tokens,
        }
    )

    return {
        "respuesta": respuesta,
        "traza": traza_eventos,
        "fuentes": fuentes,
        "latencia_ms": latencia_ms,
        "tokens": tokens,
    }


@app.websocket("/ws/voz/{session_id}")
async def voz(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    await _obtener_sesion(session_id, crear=True)
    cola = LiveRequestQueue()
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    async def subida() -> None:
        try:
            while True:
                mensaje = await websocket.receive()
                tipo = mensaje.get("type")
                if tipo == "websocket.disconnect":
                    break
                texto = mensaje.get("text")
                if texto:
                    try:
                        payload = json.loads(texto)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("tipo") == "texto":
                        cola.send_content(
                            types.Content(
                                role="user",
                                parts=[types.Part(text=str(payload.get("texto", "")))],
                            )
                        )
                    continue
                datos = mensaje.get("bytes")
                if datos:
                    cola.send_realtime(types.Blob(data=datos, mime_type="audio/pcm;rate=16000"))
        except WebSocketDisconnect:
            pass
        finally:
            cola.close()

    async def bajada() -> None:
        try:
            async for evento in runner_voz.run_live(
                user_id=USER_ID,
                session_id=session_id,
                live_request_queue=cola,
                run_config=run_config,
            ):
                resumen = traza.resumir_evento(evento)
                for item in resumen:
                    if item["tipo"] in {"tool", "tool_resultado"}:
                        traza.registrar({"tipo": "voz", "session_id": session_id, **item})
                    await websocket.send_json(item)
                if getattr(evento, "content", None) and evento.content.parts:
                    for parte in evento.content.parts:
                        if parte.inline_data and parte.inline_data.data:
                            await websocket.send_bytes(parte.inline_data.data)
                if getattr(evento, "input_transcription", None):
                    await websocket.send_json(
                        {
                            "tipo": "usuario",
                            "texto": evento.input_transcription.text or "",
                            "final": bool(evento.input_transcription.finished),
                        }
                    )
                if getattr(evento, "output_transcription", None):
                    await websocket.send_json(
                        {
                            "tipo": "agente",
                            "texto": evento.output_transcription.text or "",
                            "final": bool(evento.output_transcription.finished),
                        }
                    )
                if getattr(evento, "interrupted", None):
                    await websocket.send_json({"tipo": "interrumpido"})
                if getattr(evento, "turn_complete", None):
                    await websocket.send_json({"tipo": "turno_completo"})
                if getattr(evento, "error_message", None):
                    await websocket.send_json({"tipo": "error", "mensaje": evento.error_message})
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # pragma: no cover - fallback
            try:
                await websocket.send_json({"tipo": "error", "mensaje": str(exc)})
            except Exception:
                pass
        finally:
            cola.close()

    tareas = {
        asyncio.create_task(subida()),
        asyncio.create_task(bajada()),
    }
    try:
        done, pending = await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
        for tarea in pending:
            tarea.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for tarea in done:
            if tarea.cancelled():
                continue
            error = tarea.exception()
            if error:
                if isinstance(error, WebSocketDisconnect):
                    continue
                raise error
    finally:
        for tarea in tareas:
            if not tarea.done():
                tarea.cancel()
        await asyncio.gather(*tareas, return_exceptions=True)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


def main() -> None:
    import os

    import uvicorn

    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
