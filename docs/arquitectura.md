# Arquitectura

```mermaid
flowchart LR
    subgraph Navegador
        UI["Interfaz web<br/>chat + panel de traza"]
        MIC["Micrófono<br/>AudioWorklet PCM 16 kHz"]
        SPK["Bocina<br/>AudioWorklet PCM 24 kHz"]
    end

    subgraph Servidor["Servidor FastAPI (app/server.py)"]
        REST["POST /api/chat"]
        WS["WS /ws/voz/{sesión}"]
        RT["Runner texto<br/>gemini-2.5-flash"]
        RV["Runner voz<br/>Gemini Live (audio nativo)"]
        SES[("Sesiones ADK<br/>en memoria, compartidas")]
        AG["Agente ADK asistente_rrhh<br/>prompt v1 versionado"]
        TRZ["Traza<br/>var/trazas.jsonl"]
    end

    subgraph Tools
        T1["buscar_politica<br/>BM25 + filtro de inyección"]
        T2["consultar_empleado"]
        T3["calcular_vacaciones<br/>art. 76 LFT + reglamento"]
        T4["crear_ticket_rrhh"]
    end

    subgraph Datos
        D1["data/reglamento<br/>reglamento interno (ficticio)"]
        D2["data/lft<br/>LFT vigente (DOF)"]
        D3["data/empleados.csv<br/>(ficticio)"]
        D4[("var/rrhh.db<br/>SQLite tickets")]
    end

    GEM(("API de Gemini<br/>AI Studio"))

    UI -- JSON --> REST
    MIC -- binario --> WS
    WS -- audio + transcripciones + traza --> SPK
    WS --> UI
    REST --> RT
    WS --> RV
    RT --> AG
    RV --> AG
    RT & RV --- SES
    AG <--> GEM
    AG --> T1 & T2 & T3 & T4
    T1 --> D1 & D2
    T2 --> D3
    T4 --> D4
    REST & WS --> TRZ
```

## Flujo de una pregunta

1. El empleado escribe o habla. El texto llega a `/api/chat`; el audio llega en bloques de 100 ms al WebSocket, que lo mete en la `LiveRequestQueue` de ADK.
2. El runner pasa el mensaje y el historial de la sesión al modelo con el prompt v1 y el esquema de las cuatro tools.
3. El modelo decide qué tools llamar. `buscar_politica` devuelve artículos completos con su fuente, ya filtrados contra instrucciones inyectadas, y un aviso de que son datos.
4. El modelo responde citando las fuentes. En texto, el servidor devuelve la respuesta con la traza (tools, argumentos, fuentes, latencia y tokens). En voz, manda audio, transcripciones y los mismos eventos de traza por el WebSocket.
5. Si no hay información o el caso requiere a una persona, el agente crea un ticket en SQLite y le da el folio al empleado.

## Decisiones

Ver `docs/adr/`: framework y modelo (0001), RAG léxico (0002), voz nativa (0003), defensa contra inyección (0004), sesiones y tickets (0005).

## Componentes y archivos

| Componente | Archivo |
|---|---|
| Agente y prompt | `app/agent.py`, `prompts/agente_rrhh.v1.md` |
| Búsqueda | `app/rag.py` |
| Filtro de inyección | `app/seguridad.py` |
| Tools | `app/tools/` |
| API y voz | `app/server.py` |
| Traza | `app/traza.py` |
| Interfaz | `app/static/` |
