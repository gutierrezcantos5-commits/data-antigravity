# Decision Memory (Fase 3)

Lecciones aprendidas curadas, enlazadas a `error_code` y `task_id`.

## Cuándo escribir una lección

Solo cuando se **resuelve** un problema técnico no trivial (bug, formato, herramienta, convención).

No volcar chats completos: 1 lección = 1 problema + 1 solución verificable.

## Comandos

```bash
# Antes de iniciar tarea (orquestador)
python scripts/preflight_task.py engineering

# Briefing solo de memoria
python scripts/decision_memory.py --briefing --profile engineering

# Añadir lección manual
python scripts/decision_memory.py --add --domain engineering --title "..." --problem "..." --resolution "..."

# Promover incidencia cerrada a lección
python scripts/decision_memory.py --from-incident PROT-VALLE-0B-REV03 INC-001 --resolution "..."

# Buscar
python scripts/decision_memory.py --search --error-code PDF_ANNOTATED_MISSING

# Búsqueda semántica local (TF-IDF / sentence-transformers)
python scripts/memory_semantic_search.py --query "celdas fusionadas RCC"

# ChromaDB persistente (compartido con MCP `chroma` en Cursor)
python scripts/index_memory_chroma.py
python scripts/index_memory_chroma.py --query "entregable borrado git" --top 3
python scripts/preflight_task.py engineering --chroma
```

## Estructura

- `index.json` — índice machine-readable (versionado)
- `engineering/*.md`, `software/*.md`, … — texto humano
- `_TEMPLATE.md` — plantilla
