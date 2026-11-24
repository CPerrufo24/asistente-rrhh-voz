"""Definición del agente de RRHH con Google ADK."""

from google.adk.agents import Agent
from google.genai import types

from app import config
from app.tools.empleados import consultar_empleado
from app.tools.politicas import buscar_politica
from app.tools.tickets import crear_ticket_rrhh
from app.tools.vacaciones import calcular_vacaciones

HERRAMIENTAS = [buscar_politica, consultar_empleado, calcular_vacaciones, crear_ticket_rrhh]


def cargar_prompt(version: str = config.VERSION_PROMPT) -> str:
    """Lee el prompt versionado de prompts/agente_rrhh.<version>.md (sin el encabezado de notas)."""
    texto = (config.DIR_PROMPTS / f"agente_rrhh.{version}.md").read_text(encoding="utf-8")
    return texto.split("<!-- PROMPT -->", 1)[-1].strip()


def crear_agente(modelo: str = config.MODELO_TEXTO) -> Agent:
    return Agent(
        name="asistente_rrhh",
        model=modelo,
        description="Responde dudas de empleados sobre políticas de RRHH y escala a RRHH.",
        instruction=cargar_prompt(),
        tools=HERRAMIENTAS,
        generate_content_config=types.GenerateContentConfig(
            temperature=config.TEMPERATURA,
            max_output_tokens=config.MAX_TOKENS_SALIDA,
        ),
    )


root_agent = crear_agente()
