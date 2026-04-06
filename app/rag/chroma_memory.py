import os
import asyncio
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import chromadb
from app.config import (
    CHROMA_DIR,
    RAG_COLLECTION_NAME,
    MEMORY_DIR,
    RAG_TOP_K,
)
from app.rag.ollama_embedding import OllamaEmbeddingClient


@dataclass(frozen=True)
class MemoryDocument:
    doc_id: str
    text: str
    source_role: str
    story_id: str
    slice_id: str
    chapter_timestamp: str
    content_hash: str # [v0.2.3] 引入哈希校验


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_story_id(story_id: str) -> str:
    return (story_id or "default").strip().replace(" ", "_")


def _parse_header(text: str) -> dict[str, str]:
    header = {}
    lines = text.splitlines()[:15]
    for line in lines:
        if ":" in line:
            key, val = line.split(":", 1)
            header[key.strip().lower()] = val.strip()
    return header


def load_memory_documents(roles: list[str]) -> list[MemoryDocument]:
    documents = []
    for role_id in roles:
        role_path = MEMORY_DIR / role_id
        if not role_path.exists():
            continue
        for file_path in role_path.glob("*.md"):
            text = file_path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            header = _parse_header(text)
            slice_id = file_path.stem
            
            story_id = header.get("story id") or (slice_id.split("__")[0] if "__" in slice_id else "legacy")
            ts = header.get("chapter timestamp") or ("legacy")

            documents.append(MemoryDocument(
                doc_id=f"{role_id}::{slice_id}",
                text=text,
                source_role=role_id,
                story_id=_normalize_story_id(story_id),
                slice_id=slice_id,
                chapter_timestamp=ts,
                content_hash=_compute_hash(text)
            ))
    return documents


def _get_collection():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=RAG_COLLECTION_NAME)


def index_memory_directory(roles: list[str]) -> int:
    """[v0.2.3] 增量构建向量索引。仅对 Hash 变更的文件进行 Upsert。"""
    all_docs = load_memory_documents(roles)
    if not all_docs:
        return 0

    collection = _get_collection()
    
    # 获取现有 Metadata 以便比对 Hash
    try:
        existing = collection.get(include=["metadatas"])
        existing_hashes = {
            meta.get("slice_id"): meta.get("content_hash") 
            for meta in existing.get("metadatas", [])
        }
    except:
        existing_hashes = {}

    # 筛选真正需要更新的文档
    to_update = [
        d for d in all_docs 
        if existing_hashes.get(d.slice_id) != d.content_hash
    ]

    if not to_update:
        return 0

    embedder = OllamaEmbeddingClient()
    ids = [d.doc_id for d in to_update]
    texts = [d.text for d in to_update]
    metas = [{
        "source_role": d.source_role,
        "story_id": d.story_id,
        "slice_id": d.slice_id,
        "chapter_timestamp": d.chapter_timestamp,
        "content_hash": d.content_hash, # 存储哈希
    } for d in to_update]
    
    embeddings = embedder.embed_texts(texts)
    
    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metas,
        embeddings=embeddings
    )
    return len(to_update)


async def format_role_rag_context_async(
    story_id: str,
    target_role_id: str,
    role_scope: list[str],
    query_text: str,
    top_k: int | None = None,
) -> str:
    collection = _get_collection()
    top_k = top_k or RAG_TOP_K
    story_key = _normalize_story_id(story_id)
    
    embedder = OllamaEmbeddingClient()
    query_embeddings = embedder.embed_texts([query_text])
    if not query_embeddings:
        return ""

    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=top_k,
        where={"story_id": story_key},
        include=["documents", "metadatas", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return ""

    parts = []
    for idx, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
        score = 1.0 - dist if dist < 1.0 else 0.0
        parts.append(
            f"[RAG {idx}] score={score:.4f} source={meta.get('source_role')}\n"
            f"Slice: {meta.get('slice_id')}\n"
            f"{doc.strip()}"
        )

    return (
        f"RAG Context for {target_role_id} (Story: {story_key}):\n\n"
        + "\n\n".join(parts)
    )

# ── [v0.3] 既定事实 RAG ────────────────────────────────────────────────────────

# 既定事实与世界观使用独立的 doc_type 标记，与角色记忆切片共存于同一集合
_FACTS_DOC_TYPE = "established_facts"
_WORLD_DOC_TYPE = "world_bible"


def index_established_facts(
    story_id: str,
    run_id: int,
    facts_text: str,
    world_bible: str = "",
) -> int:
    """[v0.3] 将既定事实时间线和世界观设定索引到向量库。

    目的：角色视角生成时通过 RAG 检索这些内容作为客观锚点，
    而非依赖其他角色尚未完成的叙事切片，从根本上避免循环引用和逻辑矛盾。

    返回实际写入的文档数量。
    """
    story_key = _normalize_story_id(story_id)
    collection = _get_collection()
    embedder = OllamaEmbeddingClient()

    to_upsert_ids: list[str] = []
    to_upsert_texts: list[str] = []
    to_upsert_metas: list[dict] = []

    def _maybe_add(doc_id: str, text: str, doc_type: str) -> None:
        if not text.strip():
            return
        content_hash = _compute_hash(text)
        # 检查既有哈希，跳过未变更内容
        try:
            existing = collection.get(ids=[doc_id], include=["metadatas"])
            existing_metas = existing.get("metadatas") or []
            if existing_metas and existing_metas[0].get("content_hash") == content_hash:
                return
        except Exception:
            pass
        to_upsert_ids.append(doc_id)
        to_upsert_texts.append(text)
        to_upsert_metas.append({
            "story_id": story_key,
            "doc_type": doc_type,
            "source_role": "__facts__",
            "slice_id": doc_id,
            "chapter_timestamp": "facts",
            "run_id": str(run_id),
            "content_hash": content_hash,
        })

    _maybe_add(f"{story_key}__facts_run{run_id}", facts_text, _FACTS_DOC_TYPE)
    if world_bible:
        _maybe_add(f"{story_key}__world_run{run_id}", world_bible, _WORLD_DOC_TYPE)

    if not to_upsert_ids:
        return 0

    embeddings = embedder.embed_texts(to_upsert_texts)
    collection.upsert(
        ids=to_upsert_ids,
        documents=to_upsert_texts,
        metadatas=to_upsert_metas,
        embeddings=embeddings,
    )
    return len(to_upsert_ids)


async def format_facts_rag_context_async(
    story_id: str,
    target_role_id: str,
    query_text: str,
    top_k: int | None = None,
) -> str:
    """[v0.3] 从既定事实和世界观向量库中检索与角色生成相关的上下文。

    与 format_role_rag_context_async 的区别：
    - 仅检索 doc_type 为 established_facts 或 world_bible 的文档。
    - 保证角色视角生成时参照的是客观事实，而非其他角色可能存在偏差的叙事。
    """
    collection = _get_collection()
    top_k = top_k or RAG_TOP_K
    story_key = _normalize_story_id(story_id)

    embedder = OllamaEmbeddingClient()
    query_embeddings = embedder.embed_texts([query_text])
    if not query_embeddings:
        return ""

    # 先查既定事实，再查世界观，合并结果
    results_facts = collection.query(
        query_embeddings=query_embeddings,
        n_results=math.ceil(top_k / 2),
        where={"$and": [{"story_id": story_key}, {"doc_type": _FACTS_DOC_TYPE}]},
        include=["documents", "metadatas", "distances"],
    )
    results_world = collection.query(
        query_embeddings=query_embeddings,
        n_results=max(1, top_k // 2),
        where={"$and": [{"story_id": story_key}, {"doc_type": _WORLD_DOC_TYPE}]},
        include=["documents", "metadatas", "distances"],
    )

    combined_docs: list[str] = []
    combined_metas: list[dict] = []
    combined_dists: list[float] = []
    for results in (results_facts, results_world):
        combined_docs.extend(results.get("documents", [[]])[0])
        combined_metas.extend(results.get("metadatas", [[]])[0])
        combined_dists.extend(results.get("distances", [[]])[0])

    if not combined_docs:
        return ""

    parts = []
    for idx, (doc, meta, dist) in enumerate(zip(combined_docs, combined_metas, combined_dists), 1):
        score = 1.0 - dist if dist < 1.0 else 0.0
        doc_type_label = "Established Facts" if meta.get("doc_type") == _FACTS_DOC_TYPE else "World Bible"
        parts.append(
            f"[{doc_type_label} {idx}] score={score:.4f}\n"
            f"{doc.strip()}"
        )

    return (
        f"Established Facts & World Bible for {target_role_id} (Story: {story_key}):\n\n"
        + "\n\n".join(parts)
    )


def persist_generated_role_slice(
    role_id: str,
    story_id: str,
    run_id: int,
    chapter_timestamp: str,
    topic: str,
    style: str,
    content: str,
) -> Path:
    story_key = _normalize_story_id(story_id)
    dest_dir = MEMORY_DIR / role_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    slice_id = f"{story_key}__chapter_{chapter_timestamp}_run{run_id}"
    file_path = dest_dir / f"{slice_id}.md"

    header = (
        f"Story ID: {story_key}\n"
        f"Role ID: {role_id}\n"
        f"Chapter Timestamp: {chapter_timestamp}\n"
        f"Run ID: {run_id}\n"
        f"Topic: {topic}\n"
        f"Style: {style}\n"
        "---\n"
    )
    file_path.write_text(header + content.strip(), encoding="utf-8")
    return file_path
