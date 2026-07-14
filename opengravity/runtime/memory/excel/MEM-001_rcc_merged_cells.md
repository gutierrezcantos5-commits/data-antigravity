---
id: MEM-001
domain: excel
profile: engineering
error_codes: [XLSX_RCC_MISSING]
task_id: PROT-VALLE-0B-REV03
created_at: 2026-07-13
title: No escribir en celdas fusionadas del RCC
---

## Problema

Al generar Excel RCC con openpyxl, fallo `AttributeError: 'MergedCell' object attribute 'value' is read-only`.

## Causa raíz

La hoja RCC usa celdas fusionadas en metadatos (filas 6–11). openpyxl no permite escribir en celdas que forman parte de un merge.

## Resolución

- Escribir solo en celdas no fusionadas conocidas (p. ej. C3, C7).
- Para celdas dudosas, comprobar `isinstance(cell, MergedCell)` o usar try/except.
- No intentar actualizar toda la fila de cabecera del RCC.

## Evitar en el futuro

- Mapear celdas editables antes de escribir.
- Probar escritura en copia del xlsx original, no en plantilla con merges desconocidos.

## Referencias

- `generar_respuesta_propiedad_rev03.py`
