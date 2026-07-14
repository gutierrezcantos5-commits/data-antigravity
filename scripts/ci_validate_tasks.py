# -*- coding: utf-8 -*-
"""
Validacion CI del Task Ledger (Antigravity).

Modo schema (default, GitHub Actions):
  - state.json parseable y coherente con la carpeta de tarea
  - deliverables.expected/produced con rutas absolutas
  - validation.last_result=passed si status=done
  - index.json de decision memory valido

Modo full (local / self-hosted):
  - Ademas comprueba que los entregables existen en disco

Uso:
  python scripts/ci_validate_tasks.py
  python scripts/ci_validate_tasks.py --full
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TASKS_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "tasks")
MEMORY_INDEX = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory", "index.json")

VALID_PROFILES = {"engineering", "software"}
VALID_STATUS = {"pending", "in_progress", "done", "blocked", "cancelled"}
SKIP_DIRS = {"_TEMPLATE"}


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_abs_path(path: str) -> bool:
    if os.path.isabs(path):
        return True
    # Windows drive letter en runners Unix no aplica; aceptar C:\... en repo Windows
    return bool(re.match(r"^[A-Za-z]:[\\/]", path))


def _discover_tasks() -> list[tuple[str, str]]:
    tasks: list[tuple[str, str]] = []
    if not os.path.isdir(TASKS_ROOT):
        return tasks
    for name in sorted(os.listdir(TASKS_ROOT)):
        if name in SKIP_DIRS or name.startswith("."):
            continue
        state_path = os.path.join(TASKS_ROOT, name, "state.json")
        if os.path.isfile(state_path):
            tasks.append((name, state_path))
    return tasks


def validate_task_schema(task_dir: str, state_path: str) -> list[str]:
    errors: list[str] = []
    try:
        state = _load_json(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{task_dir}: state.json ilegible ({exc})"]

    task_id = state.get("task_id")
    if not task_id:
        errors.append(f"{task_dir}: falta task_id")
    elif task_id != task_dir and task_id != "TEMPLATE":
        errors.append(f"{task_dir}: task_id '{task_id}' no coincide con carpeta")

    profile = state.get("profile")
    if profile not in VALID_PROFILES:
        errors.append(f"{task_dir}: profile invalido '{profile}'")

    status = state.get("status")
    if status not in VALID_STATUS:
        errors.append(f"{task_dir}: status invalido '{status}'")

    deliverables = state.get("deliverables") or {}
    expected = deliverables.get("expected") or []
    produced = deliverables.get("produced") or []

    if status == "done" and not expected:
        errors.append(f"{task_dir}: status=done pero deliverables.expected vacio")

    if status == "done" and not produced:
        errors.append(f"{task_dir}: status=done pero deliverables.produced vacio")

    for idx, path in enumerate(produced):
        if not isinstance(path, str) or not _is_abs_path(path):
            errors.append(f"{task_dir}: produced[{idx}] no es ruta absoluta: {path!r}")

    validation = state.get("validation") or {}
    if status == "done" and validation.get("last_result") != "passed":
        errors.append(
            f"{task_dir}: status=done pero validation.last_result != passed "
            f"({validation.get('last_result')!r})"
        )

    if not state.get("updated_at"):
        errors.append(f"{task_dir}: falta updated_at")

    return errors


def validate_memory_index() -> list[str]:
    errors: list[str] = []
    if not os.path.isfile(MEMORY_INDEX):
        return ["memory/index.json no encontrado"]
    try:
        index = _load_json(MEMORY_INDEX)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"memory/index.json ilegible ({exc})"]

    lessons = index.get("lessons") or []
    if not lessons:
        errors.append("memory/index.json: sin lecciones")
        return errors

    seen: set[str] = set()
    for lesson in lessons:
        lid = lesson.get("id")
        if not lid:
            errors.append("memory/index.json: leccion sin id")
            continue
        if lid in seen:
            errors.append(f"memory/index.json: id duplicado {lid}")
        seen.add(lid)
        rel = lesson.get("file") or ""
        body = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory", rel.replace("/", os.sep))
        if not os.path.isfile(body):
            errors.append(f"memory/index.json: falta archivo de leccion {rel}")
    return errors


def run_task_validator(state_path: str, schema_only: bool) -> int:
    cmd = [
        sys.executable,
        os.path.join(REPO_ROOT, "scripts", "validate_deliverables.py"),
        "--state",
        state_path,
        "--no-write-incidents",
    ]
    if schema_only:
        cmd.append("--schema-only")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def main() -> int:
    p = argparse.ArgumentParser(description="CI validate Antigravity task ledger")
    p.add_argument(
        "--full",
        action="store_true",
        help="Comprobar existencia de entregables en disco (local/self-hosted)",
    )
    args = p.parse_args()
    schema_only = not args.full

    print("=" * 60)
    print("ANTIGRAVITY CI — Task Ledger")
    print(f"Modo: {'schema-only' if schema_only else 'full (archivos en disco)'}")
    print("=" * 60)

    tasks = _discover_tasks()
    if not tasks:
        print("ERR | No hay tareas en opengravity/runtime/tasks/")
        return 1

    all_errors: list[str] = []
    validator_failures = 0

    for task_dir, state_path in tasks:
        rel = os.path.relpath(state_path, REPO_ROOT)
        schema_errors = validate_task_schema(task_dir, state_path)
        if schema_errors:
            all_errors.extend(schema_errors)
            print(f"ERR | {task_dir} | schema")
            for err in schema_errors:
                print(f"      - {err}")
            continue

        code = run_task_validator(state_path, schema_only=schema_only)
        if code != 0:
            validator_failures += 1
            print(f"ERR | {task_dir} | validate_deliverables ({rel})")
        else:
            print(f"OK  | {task_dir} | {rel}")

    memory_errors = validate_memory_index()
    if memory_errors:
        all_errors.extend(memory_errors)
        print("ERR | memory/index.json")
        for err in memory_errors:
            print(f"      - {err}")
    else:
        print("OK  | memory/index.json")

    print("=" * 60)
    total_err = len(all_errors) + validator_failures
    print(f"Resumen: tareas={len(tasks)} schema_err={len(all_errors)} validator_err={validator_failures}")
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
