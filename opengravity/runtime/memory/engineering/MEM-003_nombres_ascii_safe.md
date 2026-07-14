---
id: MEM-003
domain: engineering
profile: engineering
error_codes: [PDF_MEMORIA_MISSING, FILE_MISSING]
task_id: PROT-SAX-0F-OMEXOM
created_at: 2026-07-13
title: Nombres ASCII-safe para insumos
---

## Problema

Herramientas (Python, Git, scripts) fallaban con rutas que contienen acentos o caracteres especiales en nombres de PDF/Excel.

## Causa raiz

Encoding Windows cp1252 vs UTF-8 en terminal y paths con `` u otros caracteres corruptos.

## Resolucion

- Copiar insumos a nombres ASCII: `SAX_MEMORIA_0F.pdf`, `SAX_RRCC_COMENTADO.xlsx`.
- Referenciar siempre la copia en `state.json` inputs y scripts.
- Actualizar regex del validador para aceptar ambos patrones (VCO-SET / SAX_MEMORIA).

## Evitar en el futuro

- Primera accion al ingestar: normalizar nombres de archivo.
- No depender del nombre original del cliente en pipelines automatizados.

## Referencias

- `scripts/validate_deliverables.py` (patrones pdf_memoria)
- `generar_revision_propiedad_sax_0F.py`
