# Incidencias activas (supervisor)

> Generado/actualizado manualmente o vía validador. Preflight lee `tasks/*/incidents.json`.

## Abiertas

### PROT-VALLE-0B-REV03 (engineering)

| ID | Código | Mensaje | Acción |
|----|--------|---------|--------|
| INC-001 | FILE_MISSING | Excel Rev03 Propiedad no en disco | Regenerar o corregir ruta en `deliverables.produced` |
| INC-002 | FILE_MISSING | PDF anotado COM Rev03 no en disco | Idem — posible efecto del git cleanup |
| INC-003 | FILE_MISSING | Informe MD Rev03 no en disco | Idem |

**Causa probable:** entregables en `Proyectos/` fuera del repo; rutas en ledger pero archivos movidos/eliminados tras cleanup.

**Self-healing:** regenerar paquete Valle o restaurar desde backup/stash si aplica → revalidar.

---

## Cerradas recientemente

_(ninguna marcada resolved aún)_

---

## Comandos

```bash
python scripts/validate_deliverables.py --briefing --profile engineering
python scripts/validate_deliverables.py --list-incidents
python scripts/decision_memory.py --from-incident PROT-VALLE-0B-REV03 INC-001 --resolution "..."
```
