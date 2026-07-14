# -*- coding: utf-8 -*-
"""
Carga presets de opciones NodeODM/WebODM para tareas de ortofoto.

Uso:
  python scripts/webodm_preset.py --list
  python scripts/webodm_preset.py --preset ortofoto_ingenieria
  python scripts/webodm_preset.py --preset ortofoto_ingenieria --api
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRESETS_DIR = os.path.join(REPO_ROOT, "opengravity", "runtime", "webodm", "presets")


def list_presets() -> list[str]:
    if not os.path.isdir(PRESETS_DIR):
        return []
    return sorted(
        f[:-5] for f in os.listdir(PRESETS_DIR) if f.endswith(".json")
    )


def load_preset(name: str) -> dict:
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Preset no encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    p = argparse.ArgumentParser(description="Presets WebODM/NodeODM")
    p.add_argument("--list", action="store_true")
    p.add_argument("--preset", type=str, help="Nombre del preset (sin .json)")
    p.add_argument("--api", action="store_true", help="Salida formato API WebODM")
    args = p.parse_args()

    if args.list:
        for name in list_presets():
            data = load_preset(name)
            print(f"- {name}: {data.get('description', '')}")
        return 0

    if not args.preset:
        p.print_help()
        return 1

    data = load_preset(args.preset)
    options = data.get("options") or []

    if args.api:
        print(json.dumps(options, ensure_ascii=False, indent=2))
    else:
        print(f"# Preset: {data.get('name', args.preset)}")
        print(f"# {data.get('description', '')}\n")
        for opt in options:
            print(f"{opt['name']}={opt['value']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
