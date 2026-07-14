# -*- coding: utf-8 -*-
"""
Validador de entregables + supervisor de incidencias (Antigravity/OpenGravity).

Perfiles:
- engineering: protecciones (PDF anotado, Excel RCC, etc.)
- software: state.json + checks declarados

Feedback loop (Fase 1):
- Si falla, escribe opengravity/runtime/tasks/<id>/incidents.json
- Registra incidencias en opengravity/runtime/incidents/registry.jsonl
- El orquestador puede leer briefing previo con --briefing

Uso:
  python scripts/validate_deliverables.py --help
  python scripts/validate_deliverables.py --state opengravity/runtime/tasks/<id>/state.json
  python scripts/validate_deliverables.py --engineering-folder "C:\\path\\entregables"
  python scripts/validate_deliverables.py --briefing --profile engineering
  python scripts/validate_deliverables.py --list-incidents --profile engineering
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TASKS_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "tasks")
INCIDENTS_REGISTRY = os.path.join(REPO_ROOT, "opengravity", "runtime", "incidents", "registry.jsonl")
SCHEMA_VERSION = "1"

SUGGESTED_ACTIONS: dict[str, str] = {
    "FOLDER_MISSING": "Verificar ruta de carpeta en state.json o --engineering-folder.",
    "FILE_MISSING": "Regenerar el entregable o corregir la ruta en deliverables.produced.",
    "FILE_EMPTY": "Regenerar el archivo; comprobar bloqueos (PDF abierto) o permisos.",
    "PDF_MEMORIA_MISSING": "Copiar PDF memoria con nombre ASCII (ej. SAX_MEMORIA_0F.pdf).",
    "PDF_ANNOTATED_MISSING": "Ejecutar script de anotacion COM; limitar paginas si el PDF es muy grande.",
    "XLSX_RCC_MISSING": "Regenerar Excel RCC; no escribir en celdas fusionadas (MergedCell).",
    "DELIVERABLES_EXPECTED_EMPTY": "Completar deliverables.expected en state.json (DoD).",
    "DELIVERABLES_PRODUCED_EMPTY": "Anadir rutas absolutas de salidas en deliverables.produced.",
    "DELIVERABLE_PATH_INVALID": "Usar rutas absolutas Windows en deliverables.produced.",
    "TESTS_RUN_EMPTY": "Registrar tests_run con comando, exit_code y resumen.",
    "STATE_INVALID": "Reparar state.json usando la plantilla _TEMPLATE.",
}


@dataclass
class CheckResult:
    ok: bool
    name: str
    detail: str = ""
    error_code: str = ""
    context: dict[str, Any] = field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_abs_path(path: str) -> bool:
    """Acepta rutas absolutas POSIX y Windows (CI corre en Linux)."""
    if os.path.isabs(path):
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", path))


def _exists_nonempty(path: str) -> CheckResult:
    if not os.path.isfile(path):
        return CheckResult(
            False,
            "file",
            f"No existe: {path}",
            "FILE_MISSING",
            {"path": path},
        )
    size = os.path.getsize(path)
    if size <= 0:
        return CheckResult(
            False,
            "file",
            f"Vacio: {path}",
            "FILE_EMPTY",
            {"path": path, "size": size},
        )
    return CheckResult(True, "file_ok", f"{os.path.basename(path)} ({size} bytes)")


def _glob_one(folder: str, pattern: str) -> str | None:
    rx = re.compile(pattern, re.IGNORECASE)
    for name in os.listdir(folder):
        if rx.search(name):
            p = os.path.join(folder, name)
            if os.path.isfile(p):
                return p
    return None


def _load_state(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _task_dir_from_state(state_path: str) -> str:
    return os.path.dirname(os.path.abspath(state_path))


def validate_from_state(state_path: str, schema_only: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        state = _load_state(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [
            CheckResult(
                False,
                "state.json",
                f"No se pudo leer state.json: {exc}",
                "STATE_INVALID",
                {"path": state_path},
            )
        ]

    results.append(_exists_nonempty(state_path))

    expected = (state.get("deliverables") or {}).get("expected") or []
    produced = (state.get("deliverables") or {}).get("produced") or []
    profile = state.get("profile") or "unknown"

    if not expected:
        results.append(
            CheckResult(
                False,
                "deliverables.expected",
                "Falta listar deliverables.expected en state.json",
                "DELIVERABLES_EXPECTED_EMPTY",
                {"profile": profile},
            )
        )
    else:
        results.append(CheckResult(True, "deliverables.expected", f"{len(expected)} items"))

    if produced:
        ok_count = 0
        for p in produced:
            if isinstance(p, str) and _is_abs_path(p):
                if schema_only:
                    results.append(
                        CheckResult(
                            True,
                            "deliverable.path",
                            f"Ruta absoluta declarada: {p}",
                        )
                    )
                    ok_count += 1
                else:
                    r = _exists_nonempty(p)
                    results.append(r)
                    ok_count += int(r.ok)
            else:
                results.append(
                    CheckResult(
                        False,
                        "deliverable",
                        f"Ruta no absoluta o invalida: {p}",
                        "DELIVERABLE_PATH_INVALID",
                        {"value": p},
                    )
                )
        results.append(CheckResult(True, "deliverables.produced", f"ok_paths={ok_count}/{len(produced)}"))
    else:
        results.append(
            CheckResult(
                False,
                "deliverables.produced",
                "Aun vacio (rellenar con rutas absolutas)",
                "DELIVERABLES_PRODUCED_EMPTY",
                {"profile": profile},
            )
        )

    if profile == "software":
        tests_run = state.get("tests_run") or []
        if tests_run:
            results.append(CheckResult(True, "tests_run", f"{len(tests_run)} entradas"))
        else:
            results.append(
                CheckResult(
                    False,
                    "tests_run",
                    "Vacio (registrar comandos y resultado)",
                    "TESTS_RUN_EMPTY",
                    {"profile": profile},
                )
            )

    return results


def validate_engineering_folder(folder: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not os.path.isdir(folder):
        return [
            CheckResult(
                False,
                "folder",
                f"No existe carpeta: {folder}",
                "FOLDER_MISSING",
                {"folder": folder},
            )
        ]

    pdf_mem = _glob_one(folder, r"(VCO-SET-ME-O-0016|SAX-SET-ME-O-0016|SAX_MEMORIA_0F).*\.pdf$")
    pdf_ann = _glob_one(folder, r"(COM_REV03|COM_.*REV03|_COM_).*(\.pdf)$")
    xlsx_rcc = _glob_one(folder, r"RCC|Hoja Revision|Revision.*VALLE.*\.xlsx$")

    if pdf_mem:
        results.append(_exists_nonempty(pdf_mem))
    else:
        results.append(
            CheckResult(
                False,
                "pdf_memoria",
                "No encuentro PDF memoria (VCO-SET / SAX-SET / SAX_MEMORIA_0F)",
                "PDF_MEMORIA_MISSING",
                {"folder": folder},
            )
        )

    if pdf_ann:
        results.append(_exists_nonempty(pdf_ann))
    else:
        results.append(
            CheckResult(
                False,
                "pdf_anotado",
                "No encuentro PDF anotado (patron COM/REV03/_COM_)",
                "PDF_ANNOTATED_MISSING",
                {"folder": folder},
            )
        )

    if xlsx_rcc:
        results.append(_exists_nonempty(xlsx_rcc))
    else:
        results.append(
            CheckResult(
                False,
                "xlsx_rcc",
                "No encuentro Excel RCC/Hoja Revision",
                "XLSX_RCC_MISSING",
                {"folder": folder},
            )
        )

    return results


def _failed_checks(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if not r.ok]


def _build_incidents_payload(
    task_id: str,
    profile: str,
    failed: list[CheckResult],
    passed: bool,
) -> dict[str, Any]:
    incidents = []
    for idx, r in enumerate(failed, start=1):
        code = r.error_code or "VALIDATION_ERROR"
        incidents.append(
            {
                "id": f"INC-{idx:03d}",
                "error_code": code,
                "severity": "error",
                "check": r.name,
                "message": r.detail,
                "context": r.context,
                "suggested_action": SUGGESTED_ACTIONS.get(code, "Revisar detalle y corregir antes de cerrar la tarea."),
                "resolved": False,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "profile": profile,
        "validated_at": _utc_now(),
        "passed": passed,
        "incidents": incidents,
    }


def _append_registry(task_id: str, profile: str, incident: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(INCIDENTS_REGISTRY), exist_ok=True)
    row = {
        "recorded_at": _utc_now(),
        "task_id": task_id,
        "profile": profile,
        **incident,
    }
    with open(INCIDENTS_REGISTRY, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_incidents(
    state_path: str | None,
    results: list[CheckResult],
    profile_override: str | None = None,
) -> str | None:
    failed = _failed_checks(results)
    passed = len(failed) == 0

    task_id = "AD-HOC"
    profile = profile_override or "engineering"
    task_dir: str | None = None

    if state_path:
        task_dir = _task_dir_from_state(state_path)
        try:
            state = _load_state(state_path)
            task_id = state.get("task_id") or os.path.basename(task_dir)
            profile = state.get("profile") or profile
        except (OSError, json.JSONDecodeError):
            task_id = os.path.basename(task_dir)

    if not task_dir:
        return None

    payload = _build_incidents_payload(task_id, profile, failed, passed)
    incidents_path = os.path.join(task_dir, "incidents.json")
    _save_json(incidents_path, payload)

    for inc in payload["incidents"]:
        _append_registry(task_id, profile, inc)

    if state_path and os.path.isfile(state_path):
        try:
            state = _load_state(state_path)
            validation = state.setdefault("validation", {})
            validation["last_run"] = payload["validated_at"]
            validation["last_result"] = "passed" if passed else "failed"
            validation["incidents_file"] = "incidents.json"
            supervisor = state.setdefault("supervisor", {})
            supervisor["last_validation"] = payload["validated_at"]
            supervisor["open_incidents"] = len(payload["incidents"])
            state["updated_at"] = payload["validated_at"][:10]
            _save_json(state_path, state)
        except (OSError, json.JSONDecodeError):
            pass

    return incidents_path


def _iter_task_incidents() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not os.path.isdir(TASKS_ROOT):
        return rows

    for name in sorted(os.listdir(TASKS_ROOT)):
        if name.startswith("_"):
            continue
        inc_path = os.path.join(TASKS_ROOT, name, "incidents.json")
        if not os.path.isfile(inc_path):
            continue
        try:
            with open(inc_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_task_folder"] = name
            rows.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def load_incidents_briefing(profile: str | None = None, limit: int = 10, unresolved_only: bool = True) -> str:
    tasks = _iter_task_incidents()
    if profile:
        tasks = [t for t in tasks if t.get("profile") == profile]

    tasks.sort(key=lambda t: t.get("validated_at") or "", reverse=True)

    lines = ["# Briefing de incidencias (supervisor)", ""]
    if profile:
        lines.append(f"Perfil: **{profile}**")
    lines.append("")

    shown = 0
    for task in tasks:
        incidents = task.get("incidents") or []
        if unresolved_only:
            incidents = [i for i in incidents if not i.get("resolved")]
        if not incidents and task.get("passed") is not False:
            continue

        shown += 1
        if shown > limit:
            break

        tid = task.get("task_id") or task.get("_task_folder")
        lines.append(f"## {tid}")
        lines.append(f"- Validado: {task.get('validated_at', 'n/d')}")
        lines.append(f"- Resultado: {'OK' if task.get('passed') else 'FALLO'}")
        for inc in incidents:
            lines.append(f"- `{inc.get('error_code')}` — {inc.get('message')}")
            action = inc.get("suggested_action")
            if action:
                lines.append(f"  - Accion: {action}")
        lines.append("")

    if shown == 0:
        lines.append("_Sin incidencias previas relevantes._")
        lines.append("")

    lines.append("## Acciones recomendadas al iniciar nueva tarea")
    lines.append("- Revisar patrones de error recurrentes arriba.")
    lines.append("- Aplicar acciones sugeridas antes de generar entregables.")
    lines.append("- Tras corregir, marcar incidencias como resolved en incidents.json.")
    lines.append("")

    return "\n".join(lines)


def list_incidents(profile: str | None = None, limit: int = 20) -> int:
    tasks = _iter_task_incidents()
    if profile:
        tasks = [t for t in tasks if t.get("profile") == profile]
    tasks.sort(key=lambda t: t.get("validated_at") or "", reverse=True)

    print("=== INCIDENCIAS POR TAREA ===")
    count = 0
    for task in tasks:
        if count >= limit:
            break
        incidents = task.get("incidents") or []
        if not incidents:
            continue
        tid = task.get("task_id") or task.get("_task_folder")
        print(f"\n[{tid}] profile={task.get('profile')} passed={task.get('passed')}")
        for inc in incidents:
            flag = "RES" if inc.get("resolved") else "OPEN"
            print(f"  {flag} | {inc.get('error_code')} | {inc.get('message')}")
        count += 1

    if count == 0:
        print("(sin incidencias registradas)")
    return 0


def _print(results: list[CheckResult]) -> int:
    ok = [r for r in results if r.ok]
    bad = _failed_checks(results)

    print("=== VALIDACION ===")
    for r in results:
        tag = "OK " if r.ok else "ERR"
        code = f" [{r.error_code}]" if (not r.ok and r.error_code) else ""
        print(f"{tag} | {r.name}{code} | {r.detail}")

    print(f"\nResumen: OK={len(ok)} ERR={len(bad)}")
    return 0 if not bad else 2


def main() -> int:
    p = argparse.ArgumentParser(description="Validador + supervisor de incidencias Antigravity")
    p.add_argument("--state", type=str, help="Ruta a state.json de la tarea")
    p.add_argument("--engineering-folder", type=str, help="Carpeta con entregables de protecciones")
    p.add_argument("--profile", type=str, help="Filtrar briefing/listado por perfil (engineering|software)")
    p.add_argument("--briefing", action="store_true", help="Imprime briefing para el orquestador")
    p.add_argument("--list-incidents", action="store_true", help="Lista incidencias de tareas previas")
    p.add_argument("--limit", type=int, default=10, help="Limite para briefing/listado")
    p.add_argument("--no-write-incidents", action="store_true", help="No escribir incidents.json")
    p.add_argument(
        "--schema-only",
        action="store_true",
        help="Solo validar state.json y rutas absolutas (sin comprobar archivos en disco; CI)",
    )
    args = p.parse_args()

    if args.briefing:
        print(load_incidents_briefing(profile=args.profile, limit=args.limit))
        return 0

    if args.list_incidents:
        return list_incidents(profile=args.profile, limit=args.limit)

    if not args.state and not args.engineering_folder:
        p.print_help()
        return 1

    all_results: list[CheckResult] = []
    if args.state:
        all_results += validate_from_state(args.state, schema_only=args.schema_only)
    if args.engineering_folder:
        all_results += validate_engineering_folder(args.engineering_folder)

    exit_code = _print(all_results)

    if not args.no_write_incidents and args.state and not args.schema_only:
        path = write_incidents(args.state, all_results)
        if path:
            if exit_code == 0:
                print(f"\nSupervisor: validacion OK -> {path}")
            else:
                print(f"\nSupervisor: incidencias registradas -> {path}")
                print("Briefing previo: python scripts/validate_deliverables.py --briefing --profile engineering")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
