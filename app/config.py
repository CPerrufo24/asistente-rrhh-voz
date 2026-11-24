"""Configuración leída de variables de entorno (ver .env.example)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = Path(os.getenv("DIR_DATOS", RAIZ / "data"))
DIR_PROMPTS = RAIZ / "prompts"
RUTA_DB = Path(os.getenv("RUTA_DB", RAIZ / "var" / "rrhh.db"))
RUTA_TRAZAS = Path(os.getenv("RUTA_TRAZAS", RAIZ / "var" / "trazas.jsonl"))

MODELO_TEXTO = os.getenv("MODELO_TEXTO", "gemini-3.5-flash-lite")
MODELO_VOZ = os.getenv("MODELO_VOZ", "gemini-3.8-live")
VERSION_PROMPT = os.getenv("VERSION_PROMPT", "v2")
