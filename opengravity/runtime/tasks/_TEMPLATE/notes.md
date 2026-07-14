## Bitácora (TEMPLATE)

### Contexto

- **Objetivo**:
- **Perfil**: A (ingeniería/protecciones) / B (software/CI)

### Línea de tiempo (corto)

- `YYYY-MM-DD HH:MM` — Inicio
- `YYYY-MM-DD HH:MM` — Evidencia clave encontrada
- `YYYY-MM-DD HH:MM` — Entregables generados

### Evidencias / referencias

- Archivo(s):
- Páginas (si aplica):
- Parámetros / settings (si aplica):

### Comandos ejecutados (si aplica)

```bash
<comando>
```

### Resultado

- Estado:
- Bloqueos:
- Próximo paso:

### Supervisor (validación)

Antes de cerrar la tarea:

```bash
python scripts/validate_deliverables.py --state opengravity/runtime/tasks/<task_id>/state.json
```

Si hay incidencias, revisar `incidents.json` y corregir antes de marcar `done`.

