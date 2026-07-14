# -*- coding: utf-8 -*-
"""
Indexa decision memory + incidencias en ChromaDB (persistente local).

Comparte almacenamiento con el MCP `chroma` (opengravity/runtime/memory/chroma_data).

Uso:
  python scripts/index_memory_chroma.py
  python scripts/index_memory_chroma.py --force
  python scripts/index_memory_chroma.py --query "celdas fusionadas RCC" --top 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from memory_semantic_search import (  # noqa: E402
    MemoryDoc,
    _corpus_hash,
    build_corpus,
    derive_query_from_profile,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEMORY_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory")
CHROMA_DATA_DIR = os.path.join(MEMORY_ROOT, "chroma_data")
MANIFEST_PATH = os.path.join(MEMORY_ROOT, "chroma_index.json")
COLLECTION_NAME = "antigravity_memory"


@dataclass
class ChromaHit:
    doc_id: str
    title: str
    kind: str
    profile: str
    error_codes: list[str]
    source: str
    text: str
    score: float


def _chroma_client():
    try:
        import chromadb
    except ImportError as exc:
        raise SystemExit(
            "chromadb no instalado. Ejecuta: pip install chromadb"
        ) from exc
    os.makedirs(CHROMA_DATA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DATA_DIR)


def _load_manifest() -> dict[str, Any]:
    if not os.path.isfile(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(corpus_hash: str, doc_count: int) -> None:
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "collection": COLLECTION_NAME,
                "corpus_hash": corpus_hash,
                "doc_count": doc_count,
                "data_dir": CHROMA_DATA_DIR,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def _doc_metadata(doc: MemoryDoc) -> dict[str, str]:
    return {
        "kind": doc.kind,
        "profile": doc.profile,
        "title": doc.title,
        "error_codes": ",".join(doc.error_codes),
        "source": doc.source,
    }


def index_memory(force: bool = False, profile: str | None = None) -> tuple[int, str]:
    docs = build_corpus(profile=None)
    corpus_hash = _corpus_hash(docs)
    manifest = _load_manifest()

    if (
        not force
        and manifest.get("corpus_hash") == corpus_hash
        and manifest.get("doc_count") == len(docs)
        and os.path.isdir(CHROMA_DATA_DIR)
    ):
        return len(docs), "unchanged"

    client = _chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"corpus_hash": corpus_hash, "schema_version": "1"},
    )

    batch_size = 50
    for start in range(0, len(docs), batch_size):
        batch = docs[start : start + batch_size]
        collection.add(
            ids=[d.doc_id for d in batch],
            documents=[d.text for d in batch],
            metadatas=[_doc_metadata(d) for d in batch],
        )

    _save_manifest(corpus_hash, len(docs))
    return len(docs), "indexed"


def _distance_to_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return max(0.0, 1.0 - float(distance))


def search_chroma(
    query: str,
    profile: str | None = None,
    top_k: int = 3,
    auto_index: bool = True,
) -> tuple[list[ChromaHit], str]:
    if auto_index:
        index_memory(force=False)

    client = _chroma_client()
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        if auto_index:
            index_memory(force=True)
            collection = client.get_collection(COLLECTION_NAME)
        else:
            return [], "missing"

    where: dict[str, Any] | None = None
    if profile:
        where = {"$or": [{"profile": profile}, {"profile": "any"}]}

    result = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits: list[ChromaHit] = []
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    for doc_id, text, meta, dist in zip(ids, documents, metadatas, distances):
        meta = meta or {}
        codes_raw = meta.get("error_codes") or ""
        codes = [c.strip() for c in codes_raw.split(",") if c.strip()]
        hits.append(
            ChromaHit(
                doc_id=doc_id,
                title=meta.get("title") or doc_id,
                kind=meta.get("kind") or "unknown",
                profile=meta.get("profile") or "any",
                error_codes=codes,
                source=meta.get("source") or "",
                text=text or "",
                score=_distance_to_score(dist),
            )
        )

    return hits, "chromadb"


def format_chroma_briefing(
    query: str,
    profile: str | None = None,
    top_k: int = 3,
) -> str:
    hits, backend = search_chroma(query, profile=profile, top_k=top_k)
    lines = [
        "# Memoria ChromaDB (top relevante)",
        "",
        f"Consulta: `{query}`",
        f"Motor: `{backend}` | Coleccion: `{COLLECTION_NAME}`",
        "",
    ]
    if not hits:
        lines.append("_Sin coincidencias (ejecuta index_memory_chroma.py --force)._")
        return "\n".join(lines)

    for i, hit in enumerate(hits, start=1):
        codes = ", ".join(f"`{c}`" for c in hit.error_codes) if hit.error_codes else "n/d"
        snippet = hit.text.replace("\n", " ")[:280]
        if len(hit.text) > 280:
            snippet += "..."
        lines += [
            f"## {i}. {hit.doc_id} — {hit.title} (sim={hit.score:.3f})",
            f"- Tipo: `{hit.kind}` | Perfil: `{hit.profile}` | Codigos: {codes}",
            f"- Fuente: `{hit.source}`",
            f"- Extracto: {snippet}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Indexar / consultar memoria en ChromaDB")
    p.add_argument("--force", action="store_true", help="Reindexar aunque el corpus no cambie")
    p.add_argument("--query", "-q", type=str, help="Consulta semantica")
    p.add_argument("--profile", type=str, help="Filtrar por perfil")
    p.add_argument("--top", type=int, default=3)
    args = p.parse_args()

    if args.query:
        print(format_chroma_briefing(args.query, profile=args.profile, top_k=args.top))
        return 0

    count, status = index_memory(force=args.force)
    print(f"Chroma index {status} | docs={count} | dir={CHROMA_DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
