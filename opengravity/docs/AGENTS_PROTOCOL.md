## Protocolo de Agentes (OpenGravity / Antigravity)

> **Inicio rápido (1 página):** [`AGENTS_QUICKSTART.md`](AGENTS_QUICKSTART.md)

Este documento define **cómo deben trabajar los agentes** (especialistas y orquestador) para que el sistema sea **resiliente**, **audit-able** y **reanudable** sin depender del contexto del chat.

### Objetivo

- **A (Ingeniería/protecciones)**: responder comentarios (RCC), generar entregables (Excel/PDF/Word) y mantener trazabilidad técnica (páginas, evidencias, criterios).
- **B (Software/CI)**: implementar cambios con verificación (tests/lints/build), entregables repetibles y PRs merge-ready.

---

## Reglas operativas (obligatorias)

### 1) Fuente de verdad: Task Ledger

Toda tarea **debe** tener un directorio en `opengravity/runtime/tasks/<task_id>/` con:

- `state.json`: estado estructurado (máquina).
- `notes.md`: bitácora corta (humana).
- `incidents.json`: incidencias de validación (supervisor; se genera al validar).
- `artifacts/` (opcional): salidas/recortes/exports específicos de la tarea.

La tarea **no se considera terminada** si no existe `state.json` coherente.

### 2) Orquestador delgado

El orquestador:

- Divide problema en subtareas.
- Asigna roles (especialistas).
- Integra resultados.
- Ejecuta validaciones.

El orquestador **no** realiza extracción masiva ni redacción extensa si existe un especialista apropiado.

### 3) Evidencia o no hay cierre

Un ítem “cerrado” requiere:

- **Evidencia** (p. ej. página/tabla/setting) o
- **Justificación** (por qué no aplica) y/o
- **Acción solicitada** (qué debe cambiar en la siguiente revisión)

Esto aplica especialmente a **A (protecciones)**: cada COM debe tener trazabilidad (páginas, parámetros y contradicciones).

### 4) Puntos HITL (gates) obligatorios

Antes de cambios estructurales o entregables finales:

- Registrar en `state.json`:
  - `decisions[]` (qué y por qué)
  - `validation` (qué se comprobó)
  - `deliverables.expected[]` (qué se va a entregar)

---

## Roles recomendados (especialistas)

### Extractor/Normalizador

- Extrae PDF/Word/Excel a texto con páginas/IDs.
- Normaliza codificación/acentos.
- Produce `artifacts/extract_*.txt` o similar.

### Reviewer Técnico (A)

- Cruza evidencias con manuales (Repsol/REE/IEC).
- Señala inconsistencias y “contradicción texto vs compilado”.

### Redactor Propiedad (A)

- Produce respuestas Rev.X (tono humano).
- Mantiene consistencia (no contradicciones internas).

### Implementador (B)

- Implementa cambios.
- Mantiene el alcance, no refactors oportunistas.

### Verificador CI (B)

- Ejecuta tests/lints/build.
- Devuelve resumen de fallos y su causa raíz.

### Supervisor (Feedback Loop)

- Ejecuta `scripts/validate_deliverables.py` al cerrar una tarea.
- Si falla, escribe `incidents.json` en el directorio de la tarea.
- Antes de iniciar un lote nuevo, el orquestador **debe** ejecutar preflight:

```bash
python scripts/preflight_task.py engineering
```

(Esto combina incidencias + decision memory.)

- **Preflight memoria humana:** el orquestador debe leer `opengravity/runtime/memory/DECISION_MEMORY.md`. Si la tarea coincide con una incidencia previa, aplicar la solución registrada como **primera opción** antes de improvisar.
- **Incidencias activas:** `opengravity/runtime/incidents/INCIDENCIAS_ACTIVAS.md`

- Catálogo de códigos: `opengravity/runtime/incidents/ERROR_CODES.md`
- Registro global append-only: `opengravity/runtime/incidents/registry.jsonl`

### Decision Memory (Fase 3)

Lecciones aprendidas curadas en `opengravity/runtime/memory/`:

- `index.json` — índice por `error_code`, `domain`, `task_id`
- Promover incidencia resuelta a lección:

```bash
python scripts/decision_memory.py --from-incident PROT-VALLE-0B-REV03 INC-001 --resolution "..."
```

- Buscar antes de repetir un error: `python scripts/decision_memory.py --search --error-code PDF_ANNOTATED_MISSING`

### Observabilidad (Fase 2)

Informe semanal de salud del ecosistema:

```bash
python scripts/ecosystem_health_report.py --days 7
```

Salida por defecto: `opengravity/runtime/reports/health_YYYY-MM-DD.md`

Incluye **KPIs de agente** (tasa validación OK, cierre al 1er intento, autonomía sin incidencias) e **informe de eficiencia** con sugerencias automáticas al protocolo según incidencias recurrentes.

### Cross-Domain Bridge (Fase 4)

Validación cruzada emplazamiento (ingeniería) vs ortofoto (WebODM/KMZ/GeoTIFF):

```bash
python scripts/cross_validate.py --state opengravity/runtime/tasks/<id>/state.json
```

Manifiestos WGS84: `opengravity/runtime/geo/`. Enlazar en `state.json` → `geo_link`.

---

## Definition of Done (DoD)

### DoD-A (Ingeniería / Protecciones)

- `state.json` con:
  - `inputs` (PDF/Excel/Word)
  - `evidence_map` (páginas/ajustes)
  - `responses` (por COM o por bloque)
  - `deliverables.expected` y `deliverables.produced`
- Entregables:
  - Excel RCC actualizado (Rev.X)
  - PDF anotado (marcas COM) o informe equivalente
  - Texto/email de envío (resumen de veredicto y críticos)

### DoD-B (Software / CI)

- `state.json` con:
  - `scope` y `out_of_scope`
  - `changes` (archivos tocados)
  - `tests_run` (comando + resultado)
  - `deliverables.expected/prod`
- Checks:
  - tests/lints pasan o quedan registrados con plan de corrección
  - cambios reproducibles (comandos en notes)

