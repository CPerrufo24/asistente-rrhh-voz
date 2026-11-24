# ADR 0005: Sesiones en memoria compartidas y tickets en SQLite

- **Estado:** aceptado
- **Fecha:** 2026-11-23

## Contexto
RF-04 pide contexto dentro de la sesión, y la demo alterna texto y voz. Los tickets de escalamiento deben sobrevivir a un reinicio para que RRHH los atienda.

## Opciones consideradas
1. **`InMemorySessionService` de ADK** compartido por el runner de texto y el de voz, y tickets en SQLite en un volumen.
2. **`DatabaseSessionService` (SQLite/Postgres)** para todo. Persiste conversaciones, pero guarda datos personales de empleados sin una política de retención definida.
3. **Postgres en un contenedor aparte.** Más cercano a producción, pero agrega un servicio que puede fallar en `docker compose up` sin aportar a la demo.

## Decisión
Opción 1. La conversación vive mientras corre el servidor; los tickets se guardan en `var/rrhh.db`, montado como volumen en Docker.

## Consecuencias
- Arranque sin dependencias externas y el contexto pasa del chat a la voz dentro de la misma sesión.
- Al reiniciar se pierden las conversaciones (no los tickets). Para producción: `DatabaseSessionService` con retención definida por RRHH.
- SQLite no escala a escritura concurrente alta; para una mesa de ayuda interna sobra.
