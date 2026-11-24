# ADR 0002: RAG léxico con BM25 propio en lugar de embeddings y base vectorial

- **Estado:** aceptado
- **Fecha:** 2026-11-23

## Contexto
El corpus es chico (unos 30 artículos del reglamento interno y 24 de la LFT) y está bien estructurado: cada artículo es una unidad que se cita por su número. Los empleados preguntan con las mismas palabras de las políticas (vacaciones, aguinaldo, permiso, home office). Las pruebas deben correr en CI sin red ni llaves.

## Opciones consideradas
1. **BM25 propio sobre artículos**, con normalización en español (acentos, stopwords, raíz simple).
2. **Embeddings de Gemini + Chroma/FAISS.** Mejor con sinónimos y paráfrasis, pero agrega una llamada por consulta, una dependencia pesada y pruebas que dependen de la red.
3. **Meter todo el corpus en el prompt.** Cabe en la ventana de contexto, pero cuesta más tokens por turno, sube la latencia en voz y diluye las citas.

## Decisión
BM25 propio, un fragmento por artículo, con umbral mínimo de puntaje: si nada lo supera, la tool responde `sin_resultados` y el agente lo dice y escala.

## Consecuencias
- Cero costo y milisegundos por búsqueda; pruebas deterministas y sin red.
- La fuente es exacta ("Reglamento interno, artículo 14") porque el fragmento es el artículo completo.
- Falla con sinónimos que no comparten raíz ("días libres" contra "vacaciones"). El modelo reformula y vuelve a buscar, lo que en la práctica lo compensa. Si el corpus crece a cientos de documentos, la siguiente opción es una búsqueda híbrida con embeddings.
