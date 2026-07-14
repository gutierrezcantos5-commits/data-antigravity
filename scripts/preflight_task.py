# -*- coding: utf-8 -*-
"""
Preflight obligatorio antes de iniciar una tarea en Antigravity.

Combina briefing de incidencias (Fase 1) + decision memory (Fase 3).
Opcional: memoria semántica (RAG local) con --semantic o --chroma.

Uso:
  python scripts/preflight_task.py
  python scripts/preflight_task.py engineering
  python scripts/preflight_task.py engineering --semantic
  python scripts/preflight_task.py engineering --chroma
  python scripts/preflight_task.py engineering --semantic --query "celdas fusionadas RCC"
"""

from __future__ import annotations

import argparse
import os
import sys

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from decision_memory import load_memory_briefing
from memory_semantic_search import derive_query_from_profile, format_briefing
from validate_deliverables import load_incidents_briefing


def main() -> int:
    p = argparse.ArgumentParser(description="Preflight Antigravity (incidencias + memoria)")
    p.add_argument("profile", nargs="?", default="engineering", help="engineering|software")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument(
        "--semantic",
        action="store_true",
        help="Inyectar solo lecciones/incidencias mas relevantes (embeddings locales)",
    )
    p.add_argument(
        "--chroma",
        action="store_true",
        help="Busqueda semantica via ChromaDB persistente (MCP + scripts comparten datos)",
    )
    p.add_argument("--query", type=str, help="Intencion para busqueda semantica")
    p.add_argument("--top", type=int, default=3, help="Top-K resultados semanticos")
    args = p.parse_args()

    query = args.query or derive_query_from_profile(args.profile)

    print("=" * 60)
    print("PREFLIGHT ANTIGRAVITY")
    print("=" * 60)
    print()
    print(load_incidents_briefing(profile=args.profile, limit=args.limit))
    print()
    print("=" * 60)
    print()
    if args.chroma:
        from index_memory_chroma import format_chroma_briefing

        print(format_chroma_briefing(query, profile=args.profile, top_k=args.top))
    elif args.semantic:
        print(format_briefing(query, profile=args.profile, top_k=args.top))
    else:
        print(load_memory_briefing(profile=args.profile, limit=args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
