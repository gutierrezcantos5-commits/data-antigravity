---
id: MEM-004
domain: engineering
profile: engineering
error_codes: [DELIVERABLE_PATH_INVALID, FILE_MISSING]
task_id: TEMPLATE
created_at: 2026-07-13
title: Rutas absolutas en deliverables.produced
---

## Problema

El validador no encontraba entregables listados en `state.json`.

## Causa raiz

Rutas relativas, nombres sin path completo, o archivos movidos tras cleanup del repo.

## Resolucion

- Registrar en `deliverables.produced` rutas absolutas Windows completas.
- Re-ejecutar validador al cerrar tarea: `python scripts/validate_deliverables.py --state ...`
- Tras git cleanup/stash, verificar que los entregables siguen en disco.

## Evitar en el futuro

- No marcar `status: done` sin `validation.last_result: passed`.
- Mantener entregables de proyecto fuera del repo o en rutas estables de trabajo.

## Referencias

- `opengravity/runtime/tasks/_TEMPLATE/state.json`
