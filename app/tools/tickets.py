"""Escalamiento a RRHH: crea tickets en SQLite."""

from __future__ import annotations

import sqlite3
import unicodedata
from datetime import date, datetime

from app import config

_CATEGORIAS = {
    "vacaciones",
    "nomina",
    "permisos",
    "prestaciones",
    "conducta",
    "general",
}
_ESQUEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    folio TEXT NOT NULL,
    asunto TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    categoria TEXT NOT NULL,
    numero_empleado TEXT NOT NULL,
    prioridad TEXT NOT NULL,
    estado TEXT NOT NULL,
    creado_en TEXT NOT NULL
)
"""


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))


def _normalizar_categoria(categoria: str) -> str:
    limpia = _sin_acentos(str(categoria or "")).strip().lower()
    return limpia if limpia in _CATEGORIAS else "general"


def _conectar() -> sqlite3.Connection:
    ruta = config.RUTA_DB
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.execute(_ESQUEMA)
    return conexion


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
    categoria_normalizada = _normalizar_categoria(categoria)
    prioridad = "alta" if categoria_normalizada == "conducta" else "normal"
    tiempo_respuesta = "24 horas hábiles" if prioridad == "alta" else "72 horas hábiles"
    estado = "abierto"
    creado_en = datetime.now().isoformat(timespec="seconds")

    conexion = _conectar()
    try:
        with conexion:
            siguiente_id = conexion.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM tickets"
            ).fetchone()[0]
            folio = f"RH-{date.today().year}-{siguiente_id:04d}"
            conexion.execute(
                """
                INSERT INTO tickets (
                    id, folio, asunto, descripcion, categoria,
                    numero_empleado, prioridad, estado, creado_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    siguiente_id,
                    folio,
                    str(asunto),
                    str(descripcion),
                    categoria_normalizada,
                    str(numero_empleado or ""),
                    prioridad,
                    estado,
                    creado_en,
                ),
            )
    finally:
        conexion.close()

    return {
        "folio": folio,
        "estado": estado,
        "prioridad": prioridad,
        "tiempo_respuesta_estimado": tiempo_respuesta,
        "mensaje": f"Ticket {folio} creado; RRHH responderá en {tiempo_respuesta}.",
    }


def listar_tickets() -> list[dict]:
    """Devuelve todos los tickets registrados, del más antiguo al más reciente."""
    ruta = config.RUTA_DB
    if not ruta.is_file():
        return []
    conexion = _conectar()
    conexion.row_factory = sqlite3.Row
    try:
        filas = conexion.execute(
            """
            SELECT id, folio, asunto, descripcion, categoria, numero_empleado,
                   prioridad, estado, creado_en
            FROM tickets
            ORDER BY id
            """
        ).fetchall()
    finally:
        conexion.close()
    return [dict(fila) for fila in filas]
