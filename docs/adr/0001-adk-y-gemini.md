# ADR 0001: Google ADK con Gemini como framework y modelo

- **Estado:** aceptado
- **Fecha:** 2026-11-23

## Contexto
El agente atiende a empleados por texto y por voz, usa varias tools (búsqueda, directorio, cálculo, tickets) y necesita sesiones para mantener el contexto. El evaluador debe poder correrlo con su propia llave sin pagar, y la voz debe ser en tiempo real con interrupciones.

## Opciones consideradas
1. **Google ADK + Gemini.** Tools a partir de funciones de Python con docstring, sesiones, `run_live` para audio bidireccional con la Live API, capa gratuita en AI Studio.
2. **OpenAI Agents SDK + Realtime API.** Buen tool calling y voz de calidad, pero sin capa gratuita: el evaluador pagaría cada prueba.
3. **LangGraph + cualquier modelo + STT/TTS aparte.** Máximo control del grafo, pero hay que armar sesiones, streaming de audio e interrupciones a mano.

## Decisión
ADK 2.15 con `gemini-3.5-flash-lite` para texto y `gemini-3.8-live` para voz, los dos configurables por variable de entorno. El mismo agente (prompt y tools) sirve a los dos canales; solo cambia el modelo.

## Consecuencias
- Un solo stack para texto y voz, y las sesiones de ADK se comparten entre ambos canales.
- Se midió con los 12 casos de evaluación: `gemini-3.8-flash` acertó 12/12 con mediana de 8.7 s; `gemini-3.5-flash-lite` acertó 12/12 con 1.4 s y menos tokens. Para preguntas frecuentes con tools, el modelo ligero basta y la latencia importa más (sobre todo en voz).
- Dependemos de un proveedor. Mitigación: las tools son funciones de Python puras y el RAG no usa servicios de Google, así que migrar es cambiar la capa del agente.
- `run_live` está marcado como experimental en ADK: puede cambiar entre versiones, por eso la versión queda fija en `uv.lock`.
