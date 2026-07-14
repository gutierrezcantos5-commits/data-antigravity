## Arquitectura del Ecosistema de Agentes (Cursor + OpenGravity)

Este documento describe la arquitectura de alto nivel para un ecosistema de agentes en Antigravity, con dos líneas de uso:

- **A: Ingeniería/Protecciones** (revisión de memorias, RCC, evidencias por página, respuesta como propiedad).
- **B: Software/CI** (cambios de código, validación, PRs, auto-healing).

---

## Principios

- **Persistencia**: el estado vive en el repo (Task Ledger), no en el chat.
- **Especialización**: agentes con prompts muy enfocados.
- **Reanudabilidad**: cualquier agente puede retomar desde `state.json`.
- **Observabilidad**: cada acción relevante deja rastro (notes + logs).
- **Validación**: no se cierra nada sin evidence/justificación.

---

## Componentes

### 1) Task Ledger (estado compartido)

Ruta: `opengravity/runtime/tasks/`

- Cada tarea tiene un `task_id` y un directorio propio.
- `state.json` es el contrato de interoperabilidad entre agentes.

### 2) Especialistas

- **Extractor/Normalizador**: convierte insumos en texto estructurado.
- **Reviewer Técnico A**: cruza con normativa/criterios, marca contradicciones.
- **Redactor Propiedad A**: produce respuesta final + justifica cierres.
- **Implementador B**: cambios en código.
- **Verificador CI B**: tests/lints/build y reporte.

### 3) Orquestador

Responsable de:

- Planificar subtareas y asignar especialistas.
- Fusionar resultados en un `state.json` final coherente.
- Ejecutar validaciones automáticas.
- **Preflight** antes de cada tarea: `python scripts/preflight_task.py <profile>`.

No debe “inventar” datos: si algo no está en los insumos, se marca como `unknown` y se solicita.

### 4) Decision Memory

Ruta: `opengravity/runtime/memory/`

- Lecciones curadas (1 problema = 1 solución).
- Enlazadas a `error_code` del supervisor.
- El orquestador consulta vía preflight o `@files` sobre lecciones relevantes.

---

## Flujos de trabajo

### Flujo A (Protecciones)

1. Ingesta (PDF/Excel/Word) → extracción a `artifacts/`.
2. Matriz evidencia: COM → páginas → settings → contradicciones.
3. Respuesta Rev.X (por COM) + veredicto global.
4. Entregables (Excel RCC + PDF anotado + email).
5. Validación (existencia + tamaño + “hay anotaciones” si aplica).
6. Cross-validación geo (si `geo_link` definido): `scripts/cross_validate.py`.

### Flujo B (Software)

1. Definir scope/out_of_scope.
2. Implementar cambios.
3. Ejecutar checks: lint/test/build.
4. Dejar trazas: comandos y resultados.
5. Entregables y validación final.

---

## Convención de IDs y estados

Estados estándar:

- `pending`
- `in_progress`
- `blocked`
- `done`

Para A (COM):

- `Abierto`
- `Parcial`
- `Cerrado`

---

## Convención de logs

Ruta: `opengravity/runtime/logs/`

Formato recomendado:

`timestamp | task_id | role | action | artifact | outcome`

