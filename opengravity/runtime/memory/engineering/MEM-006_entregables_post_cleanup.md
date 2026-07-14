---
id: MEM-006
domain: engineering
profile: engineering
error_codes: [FILE_MISSING]
task_id: PROT-VALLE-0B-REV03
created_at: 2026-07-13
title: Entregables fuera del repo tras git cleanup
---

## Problema

Tras git stash/reset para limpiar el repo, el validador reporta FILE_MISSING en entregables que existian.

## Causa raiz

Los entregables de protecciones viven en Proyectos/ (fuera de Git). El ledger conserva rutas absolutas pero los archivos pueden haberse perdido o nunca restaurarse del stash.

## Resolucion

- Mantener entregables en rutas estables (Google Drive / Proyectos).
- Tras cleanup git: ejecutar validador inmediatamente.
- Regenerar con scripts del proyecto o restaurar stash puntual (git stash show -p stash@{N} -- path).
- No marcar done sin validation.last_result passed.

## Evitar en el futuro

- Backup de entregables fuera del repo antes de cleanup masivo.
- Anotar en notes.md si entregables dependen de stash backup.

## Referencias

- opengravity/runtime/incidents/INCIDENCIAS_ACTIVAS.md
- MEM-004
