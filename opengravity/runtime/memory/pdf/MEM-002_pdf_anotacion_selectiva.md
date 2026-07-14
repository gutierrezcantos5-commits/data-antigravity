---
id: MEM-002
domain: pdf
profile: engineering
error_codes: [PDF_ANNOTATED_MISSING]
task_id: PROT-VALLE-0B-REV03
created_at: 2026-07-13
title: Anotar PDF grandes de forma selectiva
---

## Problema

Anotar todas las paginas de memorias de protecciones (>100 pag) generaba PDF enorme, lento o bloqueado por permisos.

## Causa raiz

Demasiadas anotaciones por pagina y reescritura del mismo archivo en uso.

## Resolucion

- Anotar solo paginas ancla por COM (1–3 paginas clave por item).
- Usar nombre de salida con fecha unico (`*_COM_REV03_12072026.pdf`).
- Cerrar visores PDF antes de regenerar; eliminar archivo cero-bytes si fallo previo.

## Evitar en el futuro

- Limitar paginas en el script de anotacion.
- Validar tamano del PDF anotado con `validate_deliverables.py`.

## Referencias

- `anotar_pdf_com_rev03.py`
