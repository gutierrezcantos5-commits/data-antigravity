# PROTOCOLO OPERATIVO — EJECUCIÓN DIARIA (Modo Orquestador)

> **Nivel 0** · Orquestador: Cursor (Composer/Agent) · Fuente de verdad: Task Ledger en repo  
> Detalle: `AGENTS_PROTOCOL.md` · Memoria humana: `opengravity/runtime/memory/DECISION_MEMORY.md`

---

## 1. INICIALIZACIÓN (Preflight — `@state.json`)

**Antes de cualquier acción productiva:**

1. Abrir `opengravity/runtime/tasks/<TASK_ID>/state.json` → identificar fase, perfil, entregables pendientes.
2. Ejecutar:
   ```bash
   python scripts/preflight_task.py engineering --semantic
   ```
   Alternativa con ChromaDB (embeddings ONNX, compartido con MCP `chroma`):
   ```bash
   python scripts/preflight_task.py engineering --chroma
   ```
   (o `software` según `profile`; añadir `--query "..."` si la tarea tiene un problema concreto)
3. Leer:
   - `opengravity/runtime/incidents/INCIDENCIAS_ACTIVAS.md` — errores abiertos
   - `opengravity/runtime/memory/DECISION_MEMORY.md` — sentido común técnico (Valle, Sax, Excel, PDF, geo)
4. Verificar repo: `git status` — working tree limpio o cambios acotados a la tarea actual.
5. **No continuar** si hay incidencias críticas sin leer (`FILE_MISSING`, `GEO_NO_OVERLAP`).

---

## 2. EJECUCIÓN (Composer / Ctrl+I)

### Delegación

| Agente | Cuándo | Skill / ruta |
|--------|--------|--------------|
| Extractor | PDF/Excel/Word → texto | `nexus_registry/` |
| Reviewer técnico | Evidencias, COM, contradicciones | Protecciones A |
| Redactor propiedad | Respuestas Rev.X | Tono humano, sin contradicciones |
| Implementador | Código, scripts | Perfil software B |

**Orquestador delgado:** planifica, delega, integra. No extrae masivamente ni redacta informes largos si hay especialista.

### Herramientas (MCPs)

Invocar **solo tras preflight OK**:

| MCP | Uso |
|-----|-----|
| antigravity-bridge | Protecciones, cables, FV, IEEE80, CCC |
| QGIS | Capas, bbox, superposición |
| Excel | RCC, matrices |
| math | Cálculos exactos |
| WebODM | Ortofotos (requiere `webodm/.webodm_token`) |
| chroma | Memoria semántica persistente (`antigravity_memory`); reindexar con `python scripts/index_memory_chroma.py` |
| docling | PDF/memorias → Markdown/tablas (modo **local**, sin cloud); solo toolgroup `conversion` |
| antigravity-bridge | Calculadoras NEXUS, búsqueda skills, Cognee (`list_engineering_calculators`, `run_engineering_calculation`) |

### Restricciones

- **No** modificar entregables finales sin `deliverables.expected` definido en `state.json`.
- **No** marcar `status: done` sin validador.
- Rutas **absolutas** en `deliverables.produced`.
- Insumos con nombres **ASCII-safe** (`SAX_MEMORIA_0F.pdf`).
- Evidencia o no hay cierre (página, setting, justificación por COM).

---

## 3. PERSISTENCIA (Post-task)

1. Actualizar `state.json` (`updated_at`, `deliverables.produced`, `decisions[]`).
2. Escribir bitácora en `notes.md`.
3. Validar:
   ```bash
   python scripts/validate_deliverables.py --state opengravity/runtime/tasks/<TASK_ID>/state.json
   python scripts/cross_validate.py --state opengravity/runtime/tasks/<TASK_ID>/state.json
   ```
4. **Si error:**
   - Leer `incidents.json` generado automáticamente.
   - Intentar **self-healing** (aplicar lección en `DECISION_MEMORY.md`).
   - Revalidar. Si persiste → HITL.
   - Promover lección: `python scripts/decision_memory.py --from-incident <TASK_ID> INC-001 --resolution "..."`
5. **Si éxito:** `validation.last_result: passed` → extraer lección si hubo aprendizaje nuevo.

**CI (GitHub Actions):** en push/PR que toque ledger o memoria:

```bash
python scripts/ci_validate_tasks.py          # schema-only (como en GitHub)
python scripts/ci_validate_tasks.py --full   # local: comprueba archivos en disco
```

Workflow: `.github/workflows/antigravity-validate.yml`

**Evals Valle/Sax (10 casos fijos):**

```bash
python scripts/run_evals.py           # CI (6 casos, sin entregables locales)
python scripts/run_evals.py --full    # 10 casos completos
pytest tests/evals -m ci -v
```

Definicion: `opengravity/runtime/evals/engineering_cases.json`

---

## 4. HITL (Human-in-the-Loop) — DETENERSE obligatoriamente

| Acción | Gate |
|--------|------|
| `git commit` / push a `main` | Aprobación explícita |
| Cambio estructura carpetas / `.gitignore` | Aprobación explícita |
| WebODM procesamiento largo (>30 min) | Confirmar espacio disco + export plan |
| Entregables finales a cliente (Excel/PDF Rev.X) | Revisión humana veredicto REC/APROBADO |

**Formato:** `Acción requerida: Confirmar [X] para proceder.`

---

## 5. GEO / WebODM (si aplica)

```bash
webodm\Iniciar WebODM.bat
webodm\Exportar Ortofoto WebODM.bat
python scripts/cross_validate.py --state opengravity/runtime/tasks/<TASK_ID>/state.json
webodm\Limpiar restos WebODM.bat    # tras exportar
```

Manifiesto: `opengravity/runtime/geo/<proyecto>.geo.json` → `state.json` → `geo_link`.

---

## 6. MANTENIMIENTO

| Frecuencia | Acción |
|------------|--------|
| Semanal | `python scripts/ecosystem_health_report.py --days 7` |
| Tras cleanup git | Revalidar rutas en `deliverables.produced` |
| Stashes >30 días | Revisar y purgar si ledger está actualizado (`git stash list`) |

---

## Comandos rápidos

```bash
python scripts/preflight_task.py engineering --semantic
python scripts/memory_semantic_search.py --query "descripcion del problema"
python scripts/validate_deliverables.py --state opengravity/runtime/tasks/<ID>/state.json
python scripts/cross_validate.py --state opengravity/runtime/tasks/<ID>/state.json
python scripts/decision_memory.py --search --error-code PDF_ANNOTATED_MISSING
python scripts/ecosystem_health_report.py --days 7
```

---

*Antigravity RuFlo V3 — El chat olvida; el ledger recuerda.*
