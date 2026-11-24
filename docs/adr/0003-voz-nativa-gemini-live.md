# ADR 0003: Voz con audio nativo de Gemini Live en lugar de cascada STT → LLM → TTS

- **Estado:** aceptado
- **Fecha:** 2026-11-23

## Contexto
El empleado llama y pregunta. Una conversación de voz se siente natural con menos de un segundo de espera y si se puede interrumpir al agente a media respuesta.

## Opciones consideradas
1. **Gemini Live con audio nativo** vía `Runner.run_live` de ADK: audio entra y sale por un mismo WebSocket, con detección de voz e interrupciones del lado del modelo.
2. **Cascada:** STT (Whisper/Deepgram) → agente de texto → TTS (ElevenLabs). Cada pieza es intercambiable, pero suma tres latencias y las interrupciones hay que coordinarlas a mano.
3. **Solo voz del navegador** (Web Speech API). Gratis, pero la calidad depende del navegador y no funciona igual en todos.

## Decisión
Gemini Live nativo. El navegador manda PCM de 16 kHz por WebSocket al backend, el backend lo pasa a la `LiveRequestQueue` de ADK y regresa audio de 24 kHz, transcripciones y eventos de tools. Al recibir `interrupted`, la interfaz vacía su búfer de audio.

## Consecuencias
- Baja latencia e interrupciones reales, con las mismas tools y la misma sesión que el chat de texto.
- La llave nunca sale al navegador: el WebSocket va al backend, no directo a Google.
- La transcripción del usuario la hace el modelo y puede equivocarse con números de empleado; por eso el prompt pide confirmar datos dictados.
- Los modelos Live tienen nombres de vista previa que cambian; quedan en `MODELO_VOZ`.
