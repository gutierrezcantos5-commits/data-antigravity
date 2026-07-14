# -*- coding: utf-8 -*-
"""
Decision Memory — lecciones aprendidas curadas (Antigravity Fase 3).

Uso:
  python scripts/decision_memory.py --briefing --profile engineering
  python scripts/decision_memory.py --list
  python scripts/decision_memory.py --search --error-code PDF_ANNOTATED_MISSING
  python scripts/decision_memory.py --add --domain pdf --title "..." --problem "..." --resolution "..."
  python scripts/decision_memory.py --from-incident PROT-VALLE-0B-REV03 INC-001 --resolution "..."
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEMORY_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory")
INDEX_PATH = os.path.join(MEMORY_ROOT, "index.json")
TASKS_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "tasks")
TEMPLATE_PATH = os.path.join(MEMORY_ROOT, "_TEMPLATE.md")


def _load_index() -> dict[str, Any]:
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(data: dict[str, Any]) -> None:
    data["updated_at"] = date.today().isoformat()
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _next_mem_id(index: dict[str, Any]) -> str:
    nums = []
    for lesson in index.get("lessons") or []:
        m = re.match(r"MEM-(\d+)", lesson.get("id") or "")
        if m:
            nums.append(int(m.group(1)))
    n = max(nums) + 1 if nums else 1
    return f"MEM-{n:03d}"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return s[:48] or "lesson"


def _read_lesson_body(rel_path: str, max_lines: int = 3) -> list[str]:
    path = os.path.join(MEMORY_ROOT, rel_path.replace("/", os.sep))
    if not os.path.isfile(path):
        return ["(archivo no encontrado)"]
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else content
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("#"):
            continue
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return lines or ["(sin contenido)"]


def _filter_lessons(
    index: dict[str, Any],
    profile: str | None = None,
    domain: str | None = None,
    error_code: str | None = None,
) -> list[dict[str, Any]]:
    lessons = list(index.get("lessons") or [])
    if profile:
        lessons = [l for l in lessons if l.get("profile") == profile or l.get("profile") == "any"]
    if domain:
        lessons = [l for l in lessons if l.get("domain") == domain]
    if error_code:
        lessons = [
            l for l in lessons
            if error_code in (l.get("error_codes") or [])
        ]
    return lessons


def load_memory_briefing(profile: str | None = None, limit: int = 8) -> str:
    index = _load_index()
    lessons = _filter_lessons(index, profile=profile)
    lessons.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    lines = ["# Briefing de decision memory", ""]
    if profile:
        lines.append(f"Perfil: **{profile}**")
        lines.append("")

    shown = 0
    for lesson in lessons:
        if shown >= limit:
            break
        shown += 1
        codes = ", ".join(f"`{c}`" for c in (lesson.get("error_codes") or []))
        lines.append(f"## {lesson.get('id')} — {lesson.get('title')}")
        lines.append(f"- Dominio: `{lesson.get('domain')}` | Tarea origen: `{lesson.get('task_id')}`")
        if codes:
            lines.append(f"- Codigos: {codes}")
        for bl in _read_lesson_body(lesson.get("file") or "", max_lines=3):
            lines.append(f"- {bl}")
        lines.append("")

    if shown == 0:
        lines.append("_Sin lecciones para este filtro._")
        lines.append("")

    lines.append("Anadir leccion tras resolver incidencia:")
    lines.append("`python scripts/decision_memory.py --from-incident <task_id> <INC-xxx> --resolution \"...\"`")
    lines.append("")
    return "\n".join(lines)


def list_lessons(profile: str | None = None) -> int:
    index = _load_index()
    lessons = _filter_lessons(index, profile=profile)
    print("=== DECISION MEMORY ===")
    for l in lessons:
        codes = ",".join(l.get("error_codes") or [])
        print(f"{l.get('id')} | {l.get('domain')} | {l.get('title')} | codes={codes}")
    print(f"\nTotal: {len(lessons)}")
    return 0


def search_lessons(error_code: str | None, domain: str | None, profile: str | None) -> int:
    index = _load_index()
    lessons = _filter_lessons(index, profile=profile, domain=domain, error_code=error_code)
    print("# Busqueda decision memory\n")
    if not lessons:
        print("_Sin resultados._")
        if error_code:
            print(f"\n(No hay leccion para `{error_code}`. Considera crear una con --add.)")
        return 0
    for lesson in lessons:
        codes = ", ".join(f"`{c}`" for c in (lesson.get("error_codes") or []))
        print(f"## {lesson.get('id')} — {lesson.get('title')}")
        print(f"- Dominio: `{lesson.get('domain')}` | Codigos: {codes}")
        for bl in _read_lesson_body(lesson.get("file") or ""):
            print(f"- {bl}")
        print()
    return 0


def add_lesson(
    domain: str,
    title: str,
    problem: str,
    resolution: str,
    profile: str = "engineering",
    error_codes: list[str] | None = None,
    task_id: str = "",
) -> int:
    index = _load_index()
    mem_id = _next_mem_id(index)
    rel_dir = domain if domain in ("engineering", "software", "webodm", "pdf", "excel") else "engineering"
    filename = f"{mem_id}_{_slug(title)}.md"
    rel_file = f"{rel_dir}/{filename}"
    path = os.path.join(MEMORY_ROOT, rel_dir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    codes_yaml = json.dumps(error_codes or [])
    content = f"""---
id: {mem_id}
domain: {domain}
profile: {profile}
error_codes: {codes_yaml}
task_id: {task_id}
created_at: {date.today().isoformat()}
title: {json.dumps(title, ensure_ascii=False)}
---

## Problema

{problem}

## Resolucion

{resolution}

## Evitar en el futuro

- (Completar checklist)

## Referencias

- 
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    index.setdefault("lessons", []).append(
        {
            "id": mem_id,
            "domain": domain,
            "profile": profile,
            "error_codes": error_codes or [],
            "task_id": task_id,
            "created_at": date.today().isoformat(),
            "title": title,
            "file": rel_file,
        }
    )
    _save_index(index)
    print(f"Leccion creada: {mem_id} -> {rel_file}")
    return 0


def from_incident(task_id: str, incident_id: str, resolution: str, title: str = "") -> int:
    inc_path = os.path.join(TASKS_ROOT, task_id, "incidents.json")
    if not os.path.isfile(inc_path):
        print(f"No existe {inc_path}")
        return 1

    with open(inc_path, "r", encoding="utf-8") as f:
        inc_doc = json.load(f)

    incident = None
    for inc in inc_doc.get("incidents") or []:
        if inc.get("id") == incident_id:
            incident = inc
            break
    if not incident:
        print(f"Incidencia {incident_id} no encontrada en {task_id}")
        return 1

    code = incident.get("error_code") or "UNKNOWN"
    domain_map = {
        "PDF_ANNOTATED_MISSING": "pdf",
        "PDF_MEMORIA_MISSING": "pdf",
        "XLSX_RCC_MISSING": "excel",
        "FILE_MISSING": "engineering",
        "DELIVERABLE_PATH_INVALID": "engineering",
    }
    domain = domain_map.get(code, "engineering")
    profile = inc_doc.get("profile") or "engineering"
    lesson_title = title or f"Resuelto: {code} en {task_id}"
    problem = incident.get("message") or ""

    result = add_lesson(
        domain=domain,
        title=lesson_title,
        problem=problem,
        resolution=resolution,
        profile=profile,
        error_codes=[code],
        task_id=task_id,
    )

    incident["resolved"] = True
    incident["resolution"] = resolution
    incident["memory_promoted"] = True
    with open(inc_path, "w", encoding="utf-8") as f:
        json.dump(inc_doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Decision Memory Antigravity")
    p.add_argument("--briefing", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--search", action="store_true")
    p.add_argument("--add", action="store_true")
    p.add_argument("--from-incident", nargs=2, metavar=("TASK_ID", "INC_ID"))
    p.add_argument("--profile", type=str)
    p.add_argument("--domain", type=str)
    p.add_argument("--error-code", type=str)
    p.add_argument("--title", type=str)
    p.add_argument("--problem", type=str)
    p.add_argument("--resolution", type=str)
    p.add_argument("--task-id", type=str, default="")
    p.add_argument("--limit", type=int, default=8)
    args = p.parse_args()

    if args.briefing:
        print(load_memory_briefing(profile=args.profile, limit=args.limit))
        return 0
    if args.list:
        return list_lessons(profile=args.profile)
    if args.search:
        return search_lessons(args.error_code, args.domain, args.profile)
    if args.from_incident:
        if not args.resolution:
            print("--resolution es obligatorio con --from-incident")
            return 1
        return from_incident(args.from_incident[0], args.from_incident[1], args.resolution, args.title or "")
    if args.add:
        if not all([args.domain, args.title, args.problem, args.resolution]):
            print("--add requiere --domain --title --problem --resolution")
            return 1
        codes = [args.error_code] if args.error_code else []
        return add_lesson(
            args.domain,
            args.title,
            args.problem,
            args.resolution,
            profile=args.profile or "engineering",
            error_codes=codes,
            task_id=args.task_id,
        )

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
