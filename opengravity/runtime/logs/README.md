## Logs de runtime (OpenGravity)

Esta carpeta está pensada para trazas **ligeras** y legibles por humanos.

### Formato recomendado

`timestamp | task_id | role | action | artifact | outcome`

Ejemplo:

`2026-07-13T21:10:00 | PROT-VALLE-0B | extractor | extract_pdf | artifacts/_extract_pdf.txt | ok`

### Buenas prácticas

- Loguear solo hitos (no spam).
- Incluir rutas de artefactos cuando aplique.
- Si algo falla, registrar **causa** y **siguiente acción**.

