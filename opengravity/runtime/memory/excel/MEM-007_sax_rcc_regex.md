---
id: MEM-007
domain: excel
profile: engineering
error_codes: [XLSX_RCC_MISSING]
task_id: PROT-SAX-0F-OMEXOM
created_at: 2026-07-13
title: Extraer COM del RCC Sax con regex multilinea
---

## Problema

Al parsear SAX_RRCC_COMENTADO.xlsx algunos COM no se capturaban o el texto quedaba truncado.

## Causa raiz

Celdas RCC con saltos de linea y delimitadores inconsistentes; regex demasiado estricto.

## Resolucion

- Volcar Excel a _extract_sax_rcc.txt (UTF-8) para inspeccion.
- Regex tolerante a multilinea; ignorar delimitadores extra.
- Validar conteo COM contra hoja antes de generar informe/PDF.

## Evitar en el futuro

- Siempre generar extract intermedio en artifacts/.
- Smoke test: numero COM extraidos vs filas visibles en RCC.

## Referencias

- generar_revision_propiedad_sax_0F.py
