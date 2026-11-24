from fastapi.testclient import TestClient
from google.adk.events.event import Event
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app import server


async def fake_run_async(*, user_id, session_id, new_message):
    yield Event(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="buscar_politica",
                        args={"tema": "aguinaldo"},
                    )
                )
            ],
        )
    )
    yield Event(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        name="buscar_politica",
                        response={"resultados": [{"fuente": "politicas/aguinaldo.md"}]},
                    )
                )
            ],
        )
    )
    yield Event(
        content=types.Content(
            role="model", parts=[types.Part(text="El aguinaldo se paga en diciembre.")]
        ),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=11, candidates_token_count=9
        ),
    )


def _client(monkeypatch):
    service = InMemorySessionService()
    monkeypatch.setattr(server, "session_service", service)
    monkeypatch.setattr(server.runner_texto, "session_service", service)
    monkeypatch.setattr(server.runner_texto, "run_async", fake_run_async)
    return TestClient(server.app)


def test_salud_y_crear_sesion(monkeypatch):
    client = _client(monkeypatch)

    salud = client.get("/api/salud")
    assert salud.status_code == 200
    assert salud.json()["ok"] is True
    assert salud.json()["modelo_texto"]
    assert salud.json()["modelo_voz"]

    sesion = client.post("/api/sesiones")
    assert sesion.status_code == 200
    assert sesion.json()["session_id"]


def test_chat_devuelve_respuesta_traza_y_fuentes(monkeypatch):
    client = _client(monkeypatch)
    session_id = client.post("/api/sesiones").json()["session_id"]

    respuesta = client.post(
        "/api/chat",
        json={"session_id": session_id, "mensaje": "¿Cuándo pagan el aguinaldo?"},
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["respuesta"] == "El aguinaldo se paga en diciembre."
    assert datos["fuentes"] == ["politicas/aguinaldo.md"]
    assert datos["latencia_ms"] >= 0
    assert datos["tokens"] == {"entrada": 11, "salida": 9}
    assert datos["traza"][0]["tipo"] == "tool"
    assert datos["traza"][1]["tipo"] == "tool_resultado"


def test_chat_devuelve_404_si_no_hay_sesion(monkeypatch):
    client = _client(monkeypatch)

    respuesta = client.post(
        "/api/chat",
        json={"session_id": "inexistente", "mensaje": "Hola"},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Sesión no encontrada."


def test_chat_devuelve_422_si_el_mensaje_esta_vacio(monkeypatch):
    client = _client(monkeypatch)
    session_id = client.post("/api/sesiones").json()["session_id"]

    respuesta = client.post(
        "/api/chat",
        json={"session_id": session_id, "mensaje": "   "},
    )

    assert respuesta.status_code == 422


def test_index_devuelve_html(monkeypatch):
    client = _client(monkeypatch)

    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "Asistente de RRHH" in respuesta.text
