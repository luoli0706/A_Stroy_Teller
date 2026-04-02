import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from app.rag.ollama_embedding import OllamaEmbeddingClient


DEFAULT_CHROMA_DIR = Path(".data/rag_chroma")
DEFAULT_COLLECTION_NAME = "story_memory_slices"


@dataclass(frozen=True)
class MemoryDocument:
    doc_id: str
    text: str
    source_role: str
    story_id: str
    slice_id: str
    chapter_timestamp: str


def _normalize_story_id(story_id: str) -> str:
    value = (story_id or "").strip()
    if not value:
        return "default"
    return value.replace(" ", "_")


def _parse_header(text: str) -> dict[str, str]:
    header: dict[str, str] = {}
    wanted = {
        "story id",
        "role id",
        "chapter timestamp",
        "run id",
        "topic",
        "style",
    }
    for line in text.splitlines()[:14]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key in wanted:
            header[normalized_key] = value.strip()
    return header


def _infer_story_id(slice_stem: str, header: dict[str, str]) -> str:
    if header.get("story id"):
        return _normalize_story_id(header["story id"])
    if "__chapter_" in slice_stem:
        return _normalize_story_id(slice_stem.split("__chapter_", 1)[0])
    return "legacy"


def _infer_chapter_timestamp(slice_stem: str, header: dict[str, str]) -> str:
    if header.get("chapter timestamp"):
        return header["chapter timestamp"]
    if "__chapter_" in slice_stem:
        rest = slice_stem.split("__chapter_", 1)[1]
        return rest.split("_run", 1)[0]
    return "legacy"


def _role_memory_files(memory_dir: Path, role_id: str) -> list[Path]:
    role_path = memory_dir / role_id
    if not role_path.exists():
        return []
    return sorted(role_path.glob("*.md"))


def load_memory_documents(memory_dir: str | Path, roles: list[str]) -> list[MemoryDocument]:
    root = Path(memory_dir)
    documents: list[MemoryDocument] = []

    for role_id in roles:
        for file_path in _role_memory_files(root, role_id):
            text = file_path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            header = _parse_header(text)
            slice_id = file_path.stem
            documents.append(
                MemoryDocument(
                    doc_id=f"{role_id}::{slice_id}",
                    text=text,
                    source_role=role_id,
                    story_id=_infer_story_id(slice_id, header),
                    slice_id=slice_id,
                    chapter_timestamp=_infer_chapter_timestamp(slice_id, header),
                )
            )

    return documents


def _get_collection(chroma_dir: str | Path | None = None):
    target = Path(chroma_dir or os.getenv("RAG_CHROMA_DIR", str(DEFAULT_CHROMA_DIR)))
    target.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(target))
    collection_name = os.getenv("RAG_COLLECTION_NAME", DEFAULT_COLLECTION_NAME)
    return client.get_or_create_collection(name=collection_name)


def index_memory_directory(
    memory_dir: str | Path,
    roles: list[str],
    chroma_dir: str | Path | None = None,
) -> int:
    docs = load_memory_documents(memory_dir, roles)
    if not docs:
        return 0

    embedder = OllamaEmbeddingClient()
    collection = _get_collection(chroma_dir)

    ids = [doc.doc_id for doc in docs]
    texts = [doc.text for doc in docs]
    metas = [
        {
            "source_role": doc.source_role,
            "story_id": doc.story_id,
            "slice_id": doc.slice_id,
            "chapter_timestamp": doc.chapter_timestamp,
        }
        for doc in docs
    ]
    embeddings = embedder.embed_texts(texts)

    if len(embeddings) != len(texts):
        raise RuntimeError("Embedding count does not match memory document count.")

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metas,
        embeddings=embeddings,
    )
    return len(docs)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def format_role_rag_context(
    story_id: str,
    target_role_id: str,
    role_scope: list[str],
    query_text: str,
    top_k: int,
    chroma_dir: str | Path | None = None,
) -> str:
    collection = _get_collection(chroma_dir)
    payload = collection.get(include=["documents", "metadatas", "embeddings"])

    ids = payload.get("ids", [])
    docs = payload.get("documents", [])
    metas = payload.get("metadatas", [])
    embs = payload.get("embeddings", [])

    if not ids:
        return ""

    scope_set = set(role_scope)
    scoped_rows: list[tuple[str, dict, list[float]]] = []
    for text, meta, emb in zip(docs, metas, embs):
        role_id = str((meta or {}).get("source_role", ""))
        if role_id in scope_set and emb is not None and not isinstance(emb, (str, bytes)):
            scoped_rows.append((str(text), dict(meta or {}), [float(v) for v in list(emb)]))

    if not scoped_rows:
        return ""

    story_key = _normalize_story_id(story_id)
    same_story_rows = [row for row in scoped_rows if str(row[1].get("story_id", "")) == story_key]
    candidates = same_story_rows or scoped_rows

    query_embedding_batch = OllamaEmbeddingClient().embed_texts([query_text])
    if not query_embedding_batch:
        return ""
    query_embedding = query_embedding_batch[0]

    scored: list[tuple[float, str, dict]] = []
    for text, meta, emb in candidates:
        score = _cosine_similarity(query_embedding, emb)
        scored.append((score, text, meta))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[: max(int(top_k), 1)]

    parts: list[str] = []
    for idx, (score, text, meta) in enumerate(selected, start=1):
        parts.append(
            "\n".join(
                [
                    f"[RAG {idx}] score={score:.4f}",
                    f"source_role={meta.get('source_role', '')}",
                    f"story_id={meta.get('story_id', '')}",
                    f"slice_id={meta.get('slice_id', '')}",
                    f"chapter_timestamp={meta.get('chapter_timestamp', '')}",
                    text,
                ]
            )
        )

    if not parts:
        return ""

    return (
        f"RAG context for role={target_role_id}, story_id={story_key}. "
        "References include own and peer memory slices from the same framework when available.\n\n"
        + "\n\n".join(parts)
    )


def current_chapter_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def persist_generated_role_slice(
    memory_dir: str | Path,
    role_id: str,
    story_id: str,
    run_id: int,
    chapter_timestamp: str,
    topic: str,
    style: str,
    content: str,
) -> Path:
    root = Path(memory_dir) / role_id
    root.mkdir(parents=True, exist_ok=True)

    story_key = _normalize_story_id(story_id)
    slice_id = f"{story_key}__chapter_{chapter_timestamp}_run{run_id}"
    output_path = root / f"{slice_id}.md"

    payload = (
        f"Story ID: {story_key}\n"
        f"Role ID: {role_id}\n"
        f"Chapter Timestamp: {chapter_timestamp}\n"
        f"Run ID: {run_id}\n"
        f"Topic: {topic}\n"
        f"Style: {style}\n"
        "---\n"
        f"{content.strip()}\n"
    )
    output_path.write_text(payload, encoding="utf-8")
    return output_path
