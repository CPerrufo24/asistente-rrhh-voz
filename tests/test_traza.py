from google.adk.events.event import Event
from google.genai import types

from app.traza import resumir_evento, texto_final, uso_tokens


def test_resumir_evento_recoge_llamadas_y_fuentes():
    evento = Event(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="buscar_politica", args={"tema": "vacaciones"}
                    )
                ),
                types.Part(
                    function_response=types.FunctionResponse(
                        name="buscar_politica",
                        response={
                            "resultados": [
                                {
                                    "fuente": "data/politicas/vacaciones.md",
                                    "alerta_inyeccion": True,
                                },
                                {"fuente": "data/politicas/beneficios.md"},
                            ]
                        },
                    )
                ),
            ],
        )
    )

    assert resumir_evento(evento) == [
        {
            "tipo": "tool",
            "nombre": "buscar_politica",
            "args": {"tema": "vacaciones"},
        },
        {
            "tipo": "tool_resultado",
            "nombre": "buscar_politica",
            "fuentes": [
                "data/politicas/vacaciones.md",
                "data/politicas/beneficios.md",
            ],
            "alerta_inyeccion": True,
        },
    ]


def test_texto_final_y_uso_tokens_solo_usan_eventos_finales():
    eventos = [
        Event(
            content=types.Content(role="model", parts=[types.Part(text="borrador")]),
            partial=True,
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=3, candidates_token_count=4
            ),
        ),
        Event(
            content=types.Content(role="model", parts=[types.Part(text="Hola")]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=10, candidates_token_count=12
            ),
        ),
        Event(
            content=types.Content(role="model", parts=[types.Part(text=" mundo")]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=5, candidates_token_count=7
            ),
        ),
    ]

    assert texto_final(eventos) == "Hola mundo"
    assert uso_tokens(eventos) == {"entrada": 18, "salida": 23}
