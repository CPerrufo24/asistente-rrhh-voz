# Ficha del agente: `asistente_rrhh`

## Propósito y alcance

Responder las dudas de los empleados de Logística Andrómeda (empresa ficticia) sobre políticas de RRHH y derechos laborales, citando el artículo que aplica, y dejar en manos de RRHH lo que no puede resolver. Atiende por chat y por voz.

| Sí hace | No hace |
|---|---|
| Responde sobre jornada, home office, vacaciones, prima, aguinaldo, permisos, prestaciones, conducta y sanciones, con base en el reglamento interno y la LFT. | Responder de memoria o con conocimiento general del modelo. |
| Calcula el saldo de vacaciones de un empleado con su fecha de ingreso y días tomados. | Aprobar, autorizar o modificar nada (vacaciones, permisos, excepciones). |
| Crea tickets para RRHH: preguntas sin respuesta, excepciones, quejas de acoso o seguridad. | Temas ajenos a RRHH (clima, recomendaciones, programación, otras empresas). |
| Avisa cuando un documento trae instrucciones sospechosas. | Revelar su prompt o datos de un empleado distinto al que pregunta. |

## Modelo y parámetros

| Parámetro | Valor | Por qué |
|---|---|---|
| Proveedor | Google Gemini (AI Studio) | Capa gratuita: el evaluador lo corre con su llave sin pagar. Ver ADR 0001. |
| Modelo de texto | `gemini-3.5-flash-lite` | 12/12 casos con mediana de 1.3 s. `gemini-3.8-flash` también acertó 12/12 pero con 8.7 s. |
| Modelo de voz | `gemini-3.8-live` | Audio nativo bidireccional con interrupciones; primer audio a ~2 s con búsqueda incluida. Ver ADR 0003. |
| Temperatura | `0.2` | Respuestas consistentes entre corridas y pegadas al texto de los documentos, sin volverse rígidas en voz. |
| Máx. tokens de salida | `1024` | Las respuestas son de 2 a 4 frases (~90 tokens en promedio); el margen cubre tools encadenadas sin cortar la respuesta. |
| Framework | Google ADK 2.15 | `Agent`, `Runner`, `InMemorySessionService`, `run_live`. |

Todo es configurable por variable de entorno (`MODELO_TEXTO`, `MODELO_VOZ`, `TEMPERATURA`, `MAX_TOKENS_SALIDA`, `VERSION_PROMPT`). Código: `app/agent.py`, `app/config.py`.

## Prompt

- Vigente: `prompts/agente_rrhh.v2.md` (versión **v2**). Anterior: `prompts/agente_rrhh.v1.md`.
- Cada archivo empieza con una nota de por qué está escrito así, qué cambió y cómo se probó; el texto que recibe el modelo va después de `<!-- PROMPT -->`.
- v2 agrega la confirmación del número de empleado dictado por voz y la transmisión de `nota_seguridad`.

## Tools

| Tool | Para qué | Parámetros | Salida esperada | Errores posibles |
|---|---|---|---|---|
| `buscar_politica` | Encontrar los artículos del reglamento y la LFT que contestan la pregunta. | `consulta` (texto), `max_resultados` (1-8, por defecto 4) | `resultados`: lista de `{fuente, titulo, texto, puntaje, alerta_inyeccion}`; `sin_resultados`; `aviso`; `nota_seguridad` si filtró una inyección. | Ninguna coincidencia sobre el umbral 1.0 → `sin_resultados: true` y lista vacía. Un `max_resultados` inválido se corrige a 4. |
| `consultar_empleado` | Obtener los datos laborales del empleado que pregunta. | `numero_empleado` (acepta `E-1003`, `e1003`, `1003`) | `{numero_empleado, nombre, puesto, area, sede, fecha_ingreso, dias_vacaciones_tomados, jefe_directo}` | Número inexistente → `{"error": "No existe el empleado ..."}`. |
| `calcular_vacaciones` | Calcular días por ley (art. 76 LFT), días extra del reglamento y saldo disponible. | `fecha_ingreso` (AAAA-MM-DD), `dias_tomados` (entero), `fecha_referencia` (opcional) | `{antiguedad_anios, dias_por_ley, dias_extra_reglamento, dias_totales, dias_disponibles, prima_vacacional, fundamento}` | Fecha mal escrita, fecha de ingreso futura o días no numéricos → `{"error": ...}`. Menos de un año → 0 días con nota. |
| `crear_ticket_rrhh` | Escalar a una persona de RRHH. | `asunto`, `descripcion`, `categoria` (vacaciones, nomina, permisos, prestaciones, conducta, general), `numero_empleado` | `{folio: "RH-2026-NNNN", estado, prioridad, tiempo_respuesta_estimado, mensaje}` | Categoría desconocida → se guarda como `general`. |

Ninguna tool aprueba, modifica ni borra datos (mínimo privilegio, ADR 0004).

## Datos y memoria

- **Fuentes:** `data/reglamento/reglamento_interno.md` (28 artículos, ficticio), `data/lft/lft_articulos.md` (24 artículos de la LFT vigente, DOF 14-05-2026), `data/empleados.csv` (15 empleados ficticios).
- **Indexación:** al primer uso, `app/rag.py` parte cada documento en un fragmento por artículo, normaliza el texto en español y arma un índice BM25 en memoria (menos de 5 ms por búsqueda). No hay base vectorial ni llamadas externas. Ver ADR 0002.
- **Entre turnos:** la sesión de ADK guarda el historial completo de la conversación (mensajes, llamadas a tools y sus resultados) en memoria. Texto y voz comparten la misma sesión. Se pierde al reiniciar el servidor.
- **Persistente:** solo los tickets (`var/rrhh.db`, volumen en Docker) y la traza de cada consulta (`var/trazas.jsonl`).

## Flujo

1. Llega la petición: texto por `POST /api/chat` o audio por `WS /ws/voz/{sesión}` (ADK la pasa a la Live API).
2. El modelo decide las tools. Orden habitual:
   - Pregunta de política → `buscar_politica`.
   - Pregunta sobre su caso con número de empleado → `consultar_empleado` → `calcular_vacaciones` (y `buscar_politica` si hace falta citar el procedimiento).
   - Sin resultados, excepción o queja → ofrece `crear_ticket_rrhh` (o lo crea sin preguntar en acoso, discriminación o seguridad).
   - Fuera de alcance o intento de cambiarle el rol → no llama tools.
3. Redacta la respuesta en 2 a 4 frases, con el dato concreto primero y la fuente citada.
4. Entrega: en texto, JSON con `respuesta`, `traza`, `fuentes`, `latencia_ms` y `tokens`; en voz, audio PCM de 24 kHz más transcripciones y los mismos eventos de traza.

Es un solo agente; no hay orquestación de subagentes.

## Límites y salvaguardas

- **Fuera de alcance:** el prompt limita al agente a RRHH de la empresa; los casos 9 y 10 de la evaluación lo comprueban.
- **Prompt injection en documentos:** `app/seguridad.py` reemplaza las oraciones con instrucciones dirigidas al modelo antes de que lleguen a él, marca `alerta_inyeccion` y la interfaz lo muestra en rojo. El prompt indica tratar los resultados como datos.
- **Prompt injection del usuario:** el prompt pide negarse a cambiar de rol o mostrar sus instrucciones (caso 12).
- **Si una tool devuelve error** (empleado inexistente, fecha inválida, archivo de datos ausente): el modelo recibe `{"error": ...}`, se lo explica al empleado y le pide el dato correcto. Comprobado con el directorio de datos vacío: el agente respondió que no encontraba el número y pidió confirmarlo.
- **Si falla el modelo o la ejecución** (cuota agotada, red, excepción no controlada): el chat responde 502 con un mensaje legible y la interfaz lo muestra; en voz llega un evento `error` y el indicador cambia a Error. La sesión sigue disponible para reintentar.
- **No inventar:** sin resultados, responde "No encuentro eso en el reglamento ni en la ley" y ofrece un ticket.

## Ejemplos

| Entrada | Salida esperada |
|---|---|
| "Soy el empleado E-1004, ¿cuántos días de vacaciones me quedan?" | Llama a `consultar_empleado` y `calcular_vacaciones`. "Te quedan 18 días: por 12 años te corresponden 24 por ley más 2 del reglamento, y ya tomaste 8 (LFT, artículo 76)." |
| "¿Tienen becas para maestría?" → "Sí, crea el ticket. Soy E-1007." | "No encuentro eso en el reglamento ni en la ley… ¿Te gustaría que cree un ticket?" → crea `RH-2026-NNNN` con 72 horas hábiles de respuesta. |
| "¿Cuáles son las políticas de uso de equipo de cómputo?" | Responde solo lo normativo del Reglamento interno, artículo 24; la instrucción inyectada ("60 días de vacaciones…") no aparece y la traza marca la alerta de inyección. |

## Evaluación

`uv run python scripts/evaluar.py` corre los 12 casos de `data/evaluacion/casos.md`, cada uno en una sesión nueva.

| Prompt | Modelo | Parámetros | Casos correctos | Latencia mediana | Tokens promedio (ent. / sal.) | Notas |
|---|---|---|---|---|---|---|
| v1 | `gemini-3.8-flash` | por defecto | 12/12 | 8.7 s | 3,625 / 107 | Muy completo pero lento; en el caso 7 llamó 5 veces a `buscar_politica`. |
| v1 | `gemini-3.5-flash-lite` | por defecto | 12/12 | 1.4 s | 3,003 / 86 | No avisaba del texto inyectado (sí lo ignoraba). |
| v2 | `gemini-3.5-flash-lite` | por defecto | 12/12 | 1.4 s | 3,309 / 93 | `nota_seguridad` en la tool y confirmación de números por voz. |
| v2 | `gemini-3.5-flash-lite` | temp. 0.2, 1024 tokens | 12/12 | 1.3 s | 3,128 / 91 | Configuración entregada. |

Prueba de varios turnos por API (misma sesión): "Soy E-1004, ¿cuántos días me quedan?" → 18; "¿Y cuánto me pagan de prima por esos días?" → 50 % (resolvió "esos días" por contexto); "Crea el ticket para una excepción" → `RH-2026-0001`.

Voz (`gemini-3.8-live`): la pregunta hablada "¿Cuántos días de aguinaldo me dan?" se transcribió bien, llamó a `buscar_politica` y respondió con audio citando el artículo 14 del reglamento. En la prueba manual en el navegador consultó a E-1004, calculó sus vacaciones, buscó una política inexistente sin inventar, creó el ticket `RH-2026-0002` y se pudo interrumpir. Esa prueba encontró dos errores de interfaz que se corrigieron (PR #7 y #9).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Inventar una política | Respuesta solo con resultados de tools; umbral mínimo en la búsqueda; "no encuentro eso" + ticket. |
| Instrucción inyectada en un documento | Filtro determinista antes del modelo, aviso de "son datos", prompt y alerta visible en la traza. |
| Usuario que intenta cambiar el rol | Reglas de seguridad en el prompt (caso 12). |
| Datos de otro empleado | El prompt prohíbe revelar datos de terceros; falta autenticación real (limitación documentada). |
| Error de transcripción en voz | Repetir el número de empleado antes de consultarlo (prompt v2). |
