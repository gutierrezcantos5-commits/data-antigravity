# -*- coding: utf-8 -*-
"""
Búsqueda semántica local sobre decision memory + incidencias (RAG ligero).

Usa sentence-transformers si está instalado; si no, TF-IDF (numpy) o Jaccard.

Uso:
  python scripts/memory_semantic_search.py --query "celdas fusionadas excel RCC"
  python scripts/memory_semantic_search.py --query "entregable borrado git" --top 3
  python scripts/memory_semantic_search.py --reindex
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEMORY_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory")
INDEX_PATH = os.path.join(MEMORY_ROOT, "index.json")
REGISTRY_PATH = os.path.join(REPO_ROOT, "opengravity", "runtime", "incidents", "registry.jsonl")
CACHE_PATH = os.path.join(MEMORY_ROOT, "embeddings_cache.json")

ST_MODEL = "all-MiniLM-L6-v2"


@dataclass
class MemoryDoc:
    doc_id: str
    kind: str  # lesson | incident
    title: str
    text: str
    profile: str
    error_codes: list[str]
    source: str


@dataclass
class SearchHit:
    doc: MemoryDoc
    score: float
    backend: str


def _read_file_body(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else content.strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9áéíóúñü]+", text.lower())


def _load_lessons() -> list[MemoryDoc]:
    if not os.path.isfile(INDEX_PATH):
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)

    docs: list[MemoryDoc] = []
    for lesson in index.get("lessons") or []:
        rel = lesson.get("file") or ""
        body_path = os.path.join(MEMORY_ROOT, rel.replace("/", os.sep))
        body = _read_file_body(body_path)
        title = lesson.get("title") or lesson.get("id") or "leccion"
        codes = lesson.get("error_codes") or []
        text = (
            f"{title}. Dominio {lesson.get('domain')}. "
            f"Codigos {', '.join(codes)}. {body}"
        )
        docs.append(
            MemoryDoc(
                doc_id=lesson.get("id") or rel,
                kind="lesson",
                title=title,
                text=text,
                profile=lesson.get("profile") or "any",
                error_codes=list(codes),
                source=rel,
            )
        )
    return docs


def _load_incidents(limit: int = 40) -> list[MemoryDoc]:
    if not os.path.isfile(REGISTRY_PATH):
        return []

    rows: list[dict[str, Any]] = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    rows.sort(key=lambda r: r.get("recorded_at") or "", reverse=True)
    seen: set[str] = set()
    docs: list[MemoryDoc] = []

    for row in rows:
        if len(docs) >= limit:
            break
        key = f"{row.get('task_id')}|{row.get('error_code')}|{row.get('message')}"
        if key in seen:
            continue
        seen.add(key)

        code = row.get("error_code") or "UNKNOWN"
        msg = row.get("message") or ""
        action = row.get("suggested_action") or ""
        text = f"Incidencia {code}. {msg}. Accion sugerida: {action}"
        docs.append(
            MemoryDoc(
                doc_id=f"{row.get('task_id')}-{row.get('id', 'INC')}",
                kind="incident",
                title=f"{row.get('task_id')} — {code}",
                text=text,
                profile=row.get("profile") or "any",
                error_codes=[code],
                source=REGISTRY_PATH,
            )
        )
    return docs


def build_corpus(profile: str | None = None) -> list[MemoryDoc]:
    docs = _load_lessons() + _load_incidents()
    if profile:
        docs = [d for d in docs if d.profile in (profile, "any")]
    return docs


def _corpus_hash(docs: list[MemoryDoc]) -> str:
    payload = json.dumps([(d.doc_id, d.text) for d in docs], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class _Embedder:
    def __init__(self) -> None:
        self.backend = "jaccard"
        self._st_model = None
        self._tfidf_vocab: dict[str, int] | None = None
        self._tfidf_idf: list[float] | None = None
        self._try_sentence_transformers()

    def _try_sentence_transformers(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._st_model = SentenceTransformer(ST_MODEL)
            self.backend = "sentence-transformers"
        except ImportError:
            self._st_model = None

    def fit_transform(self, texts: list[str]) -> list[list[float]]:
        if self.backend == "sentence-transformers" and self._st_model is not None:
            vectors = self._st_model.encode(texts, normalize_embeddings=True)
            return [v.tolist() for v in vectors]
        return self._tfidf_fit_transform(texts)

    def transform(self, texts: list[str]) -> list[list[float]]:
        if self.backend == "sentence-transformers" and self._st_model is not None:
            vectors = self._st_model.encode(texts, normalize_embeddings=True)
            return [v.tolist() for v in vectors]
        return self._tfidf_transform(texts)

    def _tfidf_fit_transform(self, texts: list[str]) -> list[list[float]]:
        self.backend = "tfidf"
        self._build_vocab(texts)
        return [self._tfidf_vector(t) for t in texts]

    def _tfidf_transform(self, texts: list[str]) -> list[list[float]]:
        return [self._tfidf_vector(t) for t in texts]

    def _build_vocab(self, texts: list[str]) -> None:
        df: dict[str, int] = {}
        docs_tokens = []
        for text in texts:
            tokens = _tokenize(text)
            docs_tokens.append(tokens)
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1
        n = max(len(texts), 1)
        vocab = sorted(df.keys())
        self._tfidf_vocab = {t: i for i, t in enumerate(vocab)}
        self._tfidf_idf = [
            math.log((1 + n) / (1 + df[t])) + 1.0 for t in vocab
        ]

    def _tfidf_vector(self, text: str) -> list[float]:
        if not self._tfidf_vocab or not self._tfidf_idf:
            return _jaccard_vector(text)
        counts: dict[str, int] = {}
        tokens = _tokenize(text)
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1
        dim = len(self._tfidf_vocab)
        vec = [0.0] * dim
        denom = max(len(tokens), 1)
        for tok, c in counts.items():
            idx = self._tfidf_vocab.get(tok)
            if idx is None:
                continue
            tf = c / denom
            vec[idx] = tf * self._tfidf_idf[idx]
        return _normalize(vec)


def _jaccard_vector(text: str) -> list[float]:
    # Fallback estable: bag-of-words hash (no requiere deps)
    tokens = _tokenize(text)
    if not tokens:
        return [0.0]
    vec = [0.0] * 256
    for tok in tokens:
        vec[hash(tok) % 256] += 1.0
    return _normalize(vec)


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return vec
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        # jaccard fallback on unequal dims
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _jaccard_score(query: str, doc: str) -> float:
    q = set(_tokenize(query))
    d = set(_tokenize(doc))
    if not q or not d:
        return 0.0
    return len(q & d) / len(q | d)


def search_similar(
    query: str,
    profile: str | None = None,
    top_k: int = 3,
    use_cache: bool = True,
) -> tuple[list[SearchHit], str]:
    docs = build_corpus(profile=profile)
    if not docs:
        return [], "none"

    embedder = _Embedder()
    corpus_hash = _corpus_hash(docs)
    cache_ok = False
    doc_vectors: list[list[float]] | None = None

    if use_cache and os.path.isfile(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if (
                cache.get("corpus_hash") == corpus_hash
                and cache.get("backend") == embedder.backend
                and len(cache.get("vectors") or []) == len(docs)
            ):
                doc_vectors = cache["vectors"]
                cache_ok = True
        except (OSError, json.JSONDecodeError, KeyError):
            pass

    if doc_vectors is None:
        doc_vectors = embedder.fit_transform([d.text for d in docs])
        if use_cache:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "corpus_hash": corpus_hash,
                        "backend": embedder.backend,
                        "model": ST_MODEL if embedder.backend == "sentence-transformers" else None,
                        "vectors": doc_vectors,
                        "doc_ids": [d.doc_id for d in docs],
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

    q_vec = embedder.transform([query])[0]
    hits: list[SearchHit] = []
    for doc, vec in zip(docs, doc_vectors):
        score = _cosine(q_vec, vec)
        if embedder.backend in ("tfidf", "jaccard") and score < 0.05:
            score = max(score, _jaccard_score(query, doc.text))
        hits.append(SearchHit(doc=doc, score=score, backend=embedder.backend))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k], embedder.backend


def format_briefing(
    query: str,
    profile: str | None = None,
    top_k: int = 3,
) -> str:
    hits, backend = search_similar(query, profile=profile, top_k=top_k)
    lines = [
        "# Memoria semántica (top relevante)",
        "",
        f"Consulta: `{query}`",
        f"Motor: `{backend}`",
        "",
    ]
    if not hits:
        lines.append("_Sin coincidencias en memory/ + registry._")
        return "\n".join(lines)

    for i, hit in enumerate(hits, start=1):
        d = hit.doc
        codes = ", ".join(f"`{c}`" for c in d.error_codes) if d.error_codes else "n/d"
        snippet = d.text.replace("\n", " ")[:280]
        if len(d.text) > 280:
            snippet += "..."
        lines += [
            f"## {i}. {d.doc_id} — {d.title} (sim={hit.score:.3f})",
            f"- Tipo: `{d.kind}` | Perfil: `{d.profile}` | Codigos: {codes}",
            f"- Fuente: `{d.source}`",
            f"- Extracto: {snippet}",
            "",
        ]
    return "\n".join(lines)


def derive_query_from_profile(profile: str) -> str:
    defaults = {
        "engineering": (
            "revision protecciones RCC excel PDF entregables validacion "
            "incidencias rutas absolutas merged cells"
        ),
        "software": "tests validacion entregables software incidencias",
    }
    return defaults.get(profile, defaults["engineering"])


def main() -> int:
    p = argparse.ArgumentParser(description="Búsqueda semántica en decision memory")
    p.add_argument("--query", "-q", type=str, help="Texto de intención / problema actual")
    p.add_argument("--profile", type=str, help="Filtrar por perfil (engineering|software)")
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--reindex", action="store_true", help="Regenerar cache de embeddings")
    args = p.parse_args()

    if args.reindex:
        if os.path.isfile(CACHE_PATH):
            os.remove(CACHE_PATH)
        docs = build_corpus(profile=args.profile)
        embedder = _Embedder()
        embedder.fit_transform([d.text for d in docs])
        print(f"Reindex OK | docs={len(docs)} | backend={embedder.backend}")
        return 0

    query = args.query or derive_query_from_profile(args.profile or "engineering")
    print(format_briefing(query, profile=args.profile, top_k=args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
