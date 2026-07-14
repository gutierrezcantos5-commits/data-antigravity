# -*- coding: utf-8 -*-
"""
Informe de salud semanal del ecosistema Antigravity/OpenGravity (Fase 2 + KPIs Fase 5).

Agrega metricas desde:
- opengravity/runtime/tasks/*/state.json
- opengravity/runtime/tasks/*/incidents.json
- opengravity/runtime/incidents/registry.jsonl
- webodm/appmedia (uso de disco, si existe)

Incluye KPIs de agente e informe de eficiencia (sugerencias al protocolo).

Uso:
  python scripts/ecosystem_health_report.py
  python scripts/ecosystem_health_report.py --days 7
  python scripts/ecosystem_health_report.py --stdout
  python scripts/ecosystem_health_report.py --output path/to/report.md
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TASKS_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "tasks")
INCIDENTS_REGISTRY = os.path.join(REPO_ROOT, "opengravity", "runtime", "incidents", "registry.jsonl")
REPORTS_DIR = os.path.join(REPO_ROOT, "opengravity", "runtime", "reports")
WEBODM_MEDIA = os.path.join(REPO_ROOT, "webodm", "appmedia")
MEMORY_INDEX = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory", "index.json")


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    if "T" in value:
        value = value.split("T", 1)[0]
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _folder_size(path: str) -> int:
    if not os.path.isdir(path):
        return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def _format_bytes(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.2f} MB"
    if n >= 1024:
        return f"{n / 1024:.2f} KB"
    return f"{n} B"


def _load_json(path: str) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _iter_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    if not os.path.isdir(TASKS_ROOT):
        return tasks

    for folder in sorted(os.listdir(TASKS_ROOT)):
        if folder.startswith("_"):
            continue
        state_path = os.path.join(TASKS_ROOT, folder, "state.json")
        state = _load_json(state_path)
        if not state:
            continue
        inc_path = os.path.join(TASKS_ROOT, folder, "incidents.json")
        incidents = _load_json(inc_path)
        state["_folder"] = folder
        state["_incidents"] = incidents
        cross_path = os.path.join(TASKS_ROOT, folder, "cross_validation.json")
        state["_cross_validation"] = _load_json(cross_path)
        tasks.append(state)
    return tasks


def _load_registry(since: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not os.path.isfile(INCIDENTS_REGISTRY):
        return rows

    with open(INCIDENTS_REGISTRY, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            recorded = _parse_day(row.get("recorded_at"))
            if recorded and recorded >= since:
                rows.append(row)
    return rows


def _in_period(d: date | None, since: date, until: date) -> bool:
    if d is None:
        return False
    return since <= d <= until


def _task_duration_days(state: dict[str, Any]) -> int | None:
    start = _parse_day(state.get("created_at"))
    end = _parse_day(state.get("updated_at"))
    if start and end and end >= start:
        return (end - start).days
    return None


def _pct(num: float, den: float) -> str:
    if den <= 0:
        return "n/d"
    return f"{100.0 * num / den:.1f}%"


def _compute_kpis(all_tasks: list[dict[str, Any]], validations: dict[str, int], registry_rows: list[dict]) -> dict[str, Any]:
    done = [t for t in all_tasks if t.get("status") == "done"]
    validated_known = validations["passed"] + validations["failed"]
    pass_rate = validations["passed"] / validated_known if validated_known else None

    first_pass = sum(
        1 for t in done
        if (t.get("validation") or {}).get("last_result") == "passed"
    )
    first_pass_rate = first_pass / len(done) if done else None

    done_with_open_inc = sum(
        1 for t in done
        if any(not i.get("resolved") for i in ((t.get("_incidents") or {}).get("incidents") or []))
    )
    autonomy_rate = (len(done) - done_with_open_inc) / len(done) if done else None

    validation_runs = len(registry_rows)

    return {
        "done_tasks": len(done),
        "first_pass_count": first_pass,
        "validation_pass_rate": pass_rate,
        "first_pass_rate": first_pass_rate,
        "autonomy_rate": autonomy_rate,
        "open_incident_tasks": done_with_open_inc,
        "validation_runs_period": validation_runs,
        "incident_events_period": validation_runs,
    }


def _protocol_suggestions(
    kpis: dict[str, Any],
    validations: dict[str, int],
    error_codes: Counter[str],
    registry_codes: Counter[str],
    cross_geo: dict[str, int],
    open_incidents: int,
    webodm_bytes: int,
    memory_count: int,
) -> list[str]:
    suggestions: list[str] = []

    if error_codes.get("FILE_MISSING", 0) >= 1:
        suggestions.append(
            "DoD: tras git cleanup/stash, ejecutar validador antes de marcar done. Ver MEM-006."
        )
    if validations["unknown"] > 0:
        suggestions.append(
            "Protocolo: hacer obligatorio `validation.last_result` en state.json al cerrar cada tarea."
        )
    if kpis.get("first_pass_rate") is not None and kpis["first_pass_rate"] < 0.9:
        rate_str = f"{100.0 * kpis['first_pass_rate']:.1f}%"
        suggestions.append(
            f"Tasa cierre limpio al primer intento {rate_str}: revisar preflight + DECISION_MEMORY antes de ejecutar."
        )
    if registry_codes.get("PDF_ANNOTATED_MISSING") or error_codes.get("PDF_ANNOTATED_MISSING"):
        suggestions.append("Reforzar MEM-002 (PDF anotacion selectiva) en briefing de ingenieria.")
    if registry_codes.get("XLSX_RCC_MISSING") or error_codes.get("XLSX_RCC_MISSING"):
        suggestions.append("Reforzar MEM-001 (celdas fusionadas RCC) en scripts Excel.")
    if cross_geo["none"] > 0:
        suggestions.append("Anadir paso cross_validate al DoD-A cuando exista geo_link.")
    if open_incidents > 3:
        suggestions.append(
            "Promover incidencias resueltas a decision_memory con --from-incident para reducir recurrencia."
        )
    if webodm_bytes > 5 * 1024 ** 3:
        suggestions.append("WebODM: exportar + limpiar tras cada ortofoto (flujo bat Limpiar restos).")
    if memory_count < 5 and (open_incidents > 0 or registry_codes):
        suggestions.append("Ampliar decision memory con lecciones de incidencias recurrentes.")
    if kpis.get("validation_pass_rate") is not None and kpis["validation_pass_rate"] < 0.5:
        suggestions.append(
            "Ratio de validacion bajo: el agente debe auto-corregir con incidents.json antes de pedir HITL."
        )
    if not suggestions:
        suggestions.append("Protocolo estable. Mantener preflight semanal y validacion al cierre.")

    return suggestions


def build_report(days: int = 7) -> str:
    until = date.today()
    since = until - timedelta(days=days - 1)

    all_tasks = _iter_tasks()
    period_tasks = [
        t for t in all_tasks
        if _in_period(_parse_day(t.get("updated_at")), since, until)
        or _in_period(_parse_day(t.get("created_at")), since, until)
    ]

    status_counter = Counter(t.get("status", "unknown") for t in all_tasks)
    profile_counter = Counter(t.get("profile", "unknown") for t in all_tasks)

    validations = {"passed": 0, "failed": 0, "unknown": 0}
    open_incidents = 0
    error_codes: Counter[str] = Counter()
    cross_geo = {"passed": 0, "failed": 0, "none": 0, "red": 0, "yellow": 0}

    for t in all_tasks:
        val = (t.get("validation") or {})
        result = val.get("last_result")
        if result == "passed":
            validations["passed"] += 1
        elif result == "failed":
            validations["failed"] += 1
        else:
            validations["unknown"] += 1

        inc_doc = t.get("_incidents") or {}
        for inc in inc_doc.get("incidents") or []:
            if not inc.get("resolved"):
                open_incidents += 1
                code = inc.get("error_code") or "UNKNOWN"
                error_codes[code] += 1

        cross = t.get("_cross_validation")
        if cross:
            if cross.get("passed"):
                cross_geo["passed"] += 1
            else:
                cross_geo["failed"] += 1
            sev = cross.get("severity")
            if sev in ("red", "yellow"):
                cross_geo[sev] += 1
        elif t.get("geo_link", {}).get("manifest"):
            cross_geo["none"] += 1

    registry_rows = _load_registry(since)
    registry_codes = Counter(r.get("error_code") or "UNKNOWN" for r in registry_rows)

    durations = [d for t in period_tasks if (d := _task_duration_days(t)) is not None]
    avg_duration = sum(durations) / len(durations) if durations else None

    done_in_period = sum(1 for t in period_tasks if t.get("status") == "done")
    webodm_bytes = _folder_size(WEBODM_MEDIA)

    memory_count = 0
    memory_domains: Counter[str] = Counter()
    if os.path.isfile(MEMORY_INDEX):
        try:
            with open(MEMORY_INDEX, "r", encoding="utf-8") as f:
                mem = json.load(f)
            lessons = mem.get("lessons") or []
            memory_count = len(lessons)
            memory_domains = Counter(l.get("domain", "unknown") for l in lessons)
        except (OSError, json.JSONDecodeError):
            pass

    kpis = _compute_kpis(all_tasks, validations, registry_rows)
    protocol_suggestions = _protocol_suggestions(
        kpis, validations, error_codes, registry_codes, cross_geo, open_incidents, webodm_bytes, memory_count
    )

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    avg_str = f"{avg_duration:.1f}" if avg_duration is not None else "n/d"

    lines = [
        "# Estado de salud del ecosistema Antigravity",
        "",
        f"- **Generado:** {generated_at}",
        f"- **Ventana:** {since.isoformat()} -> {until.isoformat()} ({days} dias)",
        "",
        "## Resumen ejecutivo",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Tareas totales (ledger) | {len(all_tasks)} |",
        f"| Tareas activas en ventana | {len(period_tasks)} |",
        f"| Completadas en ventana | {done_in_period} |",
        f"| Validaciones OK / FAIL / sin dato | {validations['passed']} / {validations['failed']} / {validations['unknown']} |",
        f"| Incidencias abiertas | {open_incidents} |",
        f"| Duración media tarea (días, ventana) | {avg_str} |",
        f"| Uso disco WebODM (appmedia) | {_format_bytes(webodm_bytes)} |",
        f"| Lecciones decision memory | {memory_count} |",
        f"| Cross-geo OK / FAIL / pendiente | {cross_geo['passed']} / {cross_geo['failed']} / {cross_geo['none']} |",
        "",
        "## KPIs de agente (eficiencia)",
        "",
        "| KPI | Valor |",
        "|-----|-------|",
        f"| Tasa validacion OK (con dato) | {_pct(validations['passed'], validations['passed'] + validations['failed'])} |",
        f"| Cierre limpio al 1er intento (done + passed) | {_pct(kpis.get('first_pass_count', 0), kpis.get('done_tasks') or 0)} |",
        f"| Tareas done sin incidencias abiertas | {_pct((kpis.get('done_tasks') or 0) - kpis.get('open_incident_tasks', 0), kpis.get('done_tasks') or 0)} |",
        f"| Eventos validacion en ventana (registry) | {kpis.get('validation_runs_period', 0)} |",
        f"| Tareas con incidencias abiertas | {kpis.get('open_incident_tasks', 0)} |",
        "",
        "## Informe de eficiencia (auto-auditoria protocolo)",
        "",
        "Sugerencias derivadas de metricas e incidencias recurrentes:",
        "",
    ]

    for s in protocol_suggestions:
        lines.append(f"- {s}")

    lines.extend([
        "",
        "## Tareas por estado",
        "",
    ])

    if status_counter:
        for status, count in status_counter.most_common():
            lines.append(f"- **{status}**: {count}")
    else:
        lines.append("- _(sin tareas)_")

    lines.extend(["", "## Tareas por perfil", ""])
    for profile, count in profile_counter.most_common():
        lines.append(f"- **{profile}**: {count}")

    lines.extend(["", "## Actividad en la ventana", ""])
    if period_tasks:
        for t in sorted(period_tasks, key=lambda x: x.get("updated_at") or "", reverse=True):
            tid = t.get("task_id") or t.get("_folder")
            lines.append(
                f"- `{tid}` — status={t.get('status')} | profile={t.get('profile')} | "
                f"updated={t.get('updated_at', 'n/d')}"
            )
    else:
        lines.append("- Sin actividad registrada en el periodo.")

    lines.extend(["", "## Incidencias (supervisor)", ""])
    if error_codes:
        lines.append("### Abiertas por código (ledger)")
        for code, count in error_codes.most_common():
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("- Sin incidencias abiertas en el ledger.")

    if registry_codes:
        lines.extend(["", f"### Eventos en registry ({len(registry_rows)} en ventana)", ""])
        for code, count in registry_codes.most_common():
            lines.append(f"- `{code}`: {count}")

    lines.extend(["", "## Decision memory", ""])
    if memory_count:
        lines.append(f"- **Total lecciones:** {memory_count}")
        for dom, count in memory_domains.most_common():
            lines.append(f"- `{dom}`: {count}")
    else:
        lines.append("- Sin lecciones indexadas.")

    lines.extend(["", "## Recomendaciones", ""])
    recs: list[str] = []
    if cross_geo["failed"] > 0 or cross_geo["red"] > 0:
        recs.append("Revisar alertas rojas en cross_validation.json (emplazamiento vs ortofoto).")
    if cross_geo["none"] > 0:
        recs.append(
            f"{cross_geo['none']} tarea(s) con geo_link sin cross_validate: ejecutar scripts/cross_validate.py"
        )
    if validations["failed"] > 0:
        recs.append("Ejecutar preflight antes del proximo lote: `python scripts/preflight_task.py engineering`")
    if open_incidents > 0:
        recs.append("Cerrar incidencias resueltas marcando `resolved: true` en `incidents.json`.")
    if webodm_bytes > 5 * 1024 ** 3:
        recs.append(f"WebODM appmedia > 5 GB ({_format_bytes(webodm_bytes)}): exportar ortofotos y limpiar proyectos.")
    if validations["unknown"] == len(all_tasks) and all_tasks:
        recs.append("Ninguna tarea tiene `validation.last_result`: ejecutar el validador al cerrar entregables.")
    if not recs:
        recs.append("Ecosistema estable en la ventana analizada. Mantener validación al cierre de cada tarea.")
    for r in recs:
        lines.append(f"- {r}")

    lines.extend([
        "",
        "## Comandos útiles",
        "",
        "```bash",
        "python scripts/ecosystem_health_report.py --days 7",
        "python scripts/preflight_task.py engineering",
        "python scripts/cross_validate.py --state opengravity/runtime/tasks/<id>/state.json",
        "python scripts/decision_memory.py --list",
        "```",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Informe de salud del ecosistema Antigravity")
    p.add_argument("--days", type=int, default=7, help="Ventana en dias (default: 7)")
    p.add_argument("--output", type=str, help="Ruta de salida Markdown")
    p.add_argument("--stdout", action="store_true", help="Imprimir informe en consola")
    args = p.parse_args()

    report = build_report(days=max(1, args.days))

    if args.stdout or not args.output:
        print(report)

    out_path = args.output
    if not out_path and not args.stdout:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        out_path = os.path.join(REPORTS_DIR, f"health_{date.today().isoformat()}.md")

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        if not args.stdout:
            print(f"Informe escrito en: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
