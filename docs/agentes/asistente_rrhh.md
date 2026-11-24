# Ficha del agente: `asistente_rrhh`

| Campo | Valor |
|---|---|
| Propósito | Responder dudas de empleados sobre políticas de RRHH y derechos laborales citando la fuente, y escalar a RRHH lo que no puede resolver. |
| Usuarios | Empleados de Logística Andrómeda (empresa ficticia), por chat o por voz. |
| Framework | Google ADK 2.15 (`google.adk.agents.Agent`, `Runner`, `InMemorySessionService`, `run_live`). |
| Modelos | Texto: `gemini-3.5-flash-lite`. Voz: `gemini-3.8-live`. Configurables con `MODELO_TEXTO` y `MODELO_VOZ`. |
| Prompt | `prompts/agente_rrhh.v2.md` (vigente) y `prompts/agente_rrhh.v1.md`. Versión por `VERSION_PROMPT`. |
| Código | `app/agent.py` |

## Tools

| Tool | Entrada | Salida | Efecto |
|---|---|---|---|
| `buscar_politica` | `consulta`, `max_resultados` (1-8) | Artículos con `fuente`, `texto` (filtrado), `puntaje`, `alerta_inyeccion`; `sin_resultados`; `nota_seguridad` si filtró algo | Solo lectura |
| `consultar_empleado` | `numero_empleado` (acepta `E-1003`, `e1003`, `1003`) | Nombre, puesto, sede, fecha de ingreso, días tomados, jefe | Solo lectura |
| `calcular_vacaciones` | `fecha_ingreso`, `dias_tomados`, `fecha_referencia` | Antigüedad, días por ley, días extra del reglamento, disponibles, prima, fundamento | Cálculo puro |
| `crear_ticket_rrhh` | `asunto`, `descripcion`, `categoria`, `numero_empleado` | Folio, estado, prioridad, tiempo estimado | Escribe un ticket en SQLite |

Ninguna tool aprueba, modifica ni borra nada (mínimo privilegio, ver ADR 0004).

## Fuentes de datos

- `data/reglamento/reglamento_interno.md`: 28 artículos, ficticio. El artículo 24 trae una instrucción inyectada a propósito.
- `data/lft/lft_articulos.md`: 24 artículos de la LFT vigente (DOF 14-05-2026).
- `data/empleados.csv`: 15 empleados ficticios.

## Comportamiento esperado

1. Busca antes de responder cualquier tema de políticas; no responde de memoria.
2. Cita la fuente con su nombre exacto ("Reglamento interno, artículo 14").
3. Aplica el reglamento cuando mejora la ley, y la ley cuando el reglamento da menos.
4. Si no hay resultados, lo dice y ofrece un ticket. Crea el ticket sin preguntar en acoso, discriminación, seguridad o excepciones.
5. Rechaza temas ajenos a RRHH y cualquier intento de cambiarle el rol o ver su prompt.

## Evaluación

`uv run python scripts/evaluar.py` corre los 12 casos de `data/evaluacion/casos.md`, cada uno en una sesión nueva.

| Prompt | Modelo | Casos correctos | Latencia mediana | Tokens promedio (entrada / salida) | Notas |
|---|---|---|---|---|---|
| v1 | `gemini-3.8-flash` | 12/12 | 8.7 s | 3,625 / 107 | Respuestas muy completas, pero lento; en el caso 7 llegó a llamar 5 veces a `buscar_politica`. |
| v1 | `gemini-3.5-flash-lite` | 12/12 | 1.4 s | 3,003 / 86 | No avisaba al empleado del texto inyectado (sí lo ignoraba). |
| v2 | `gemini-3.5-flash-lite` | 12/12 | 1.4 s | 3,309 / 93 | Se agregó `nota_seguridad` en la tool y la confirmación de números por voz. El aviso al empleado sigue sin salir siempre: la traza lo muestra. |

Prueba de varios turnos por API (misma sesión): "Soy E-1004, ¿cuántos días me quedan?" → 18 días (12 años: 24 por ley + 2 del reglamento − 8 tomados); "¿Y cuánto me pagan de prima por esos días?" → 50 % (entendió "esos días" por el contexto); "Crea el ticket para una excepción" → `RH-2026-0001`.

Voz (`gemini-3.8-live` con `run_live`): "¿Cuántos días de aguinaldo me dan?" llamó a `buscar_politica` y respondió con audio citando el artículo 14 del reglamento; primer audio a ~2.1 s.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Inventar una política | Respuesta solo con resultados de tools; umbral mínimo en la búsqueda; "no encuentro eso" + ticket. |
| Instrucción inyectada en un documento | Filtro determinista antes del modelo, aviso de "son datos", prompt y alerta visible en la traza. |
| Usuario que intenta cambiar el rol | Reglas de seguridad en el prompt (casos 12 y "SYSTEM OVERRIDE"). |
| Datos de otro empleado | El prompt prohíbe revelar datos de terceros; falta autenticación real (limitación documentada). |
| Error de transcripción en voz | Repetir el número de empleado antes de consultarlo (prompt v2). |
