import os
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
            
            # 从文件名或 Header 中推断信息
            story_id = header.get("story id") or (slice_id.split("__")[0] if "__" in slice_id else "legacy")
            ts = header.get("chapter timestamp") or ("legacy")

            documents.append(MemoryDocument(
                doc_id=f"{role_id}::{slice_id}",
                text=text,
                source_role=role_id,
                story_id=_normalize_story_id(story_id),
                slice_id=slice_id,
                chapter_timestamp=ts
            ))
    return documents


def _get_collection():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=RAG_COLLECTION_NAME)


def index_memory_directory(roles: list[str]) -> int:
    """全量/增量构建向量索引。"""
    docs = load_memory_documents(roles)
    if not docs:
        return 0

    embedder = OllamaEmbeddingClient()
    collection = _get_collection()

    ids = [d.doc_id for d in docs]
    texts = [d.text for d in docs]
    metas = [{
        "source_role": d.source_role,
        "story_id": d.story_id,
        "slice_id": d.slice_id,
        "chapter_timestamp": d.chapter_timestamp,
    } for d in docs]
    
    # 批量嵌入 (同步调用，因为 OllamaEmbeddingClient 目前是同步的)
    embeddings = embedder.embed_texts(texts)
    
    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metas,
        embeddings=embeddings
    )
    return len(docs)


async def format_role_rag_context_async(
    story_id: str,
    target_role_id: str,
    role_scope: list[str],
    query_text: str,
    top_k: int | None = None,
) -> str:
    """使用 ChromaDB 的原生 query 接口进行高效异步检索。"""
    collection = _get_collection()
    top_k = top_k or RAG_TOP_K
    story_key = _normalize_story_id(story_id)
    
    # 获取查询向量
    embedder = OllamaEmbeddingClient()
    # 目前嵌入客户端是同步的，但在异步节点中运行，后续可优化为异步
    query_embeddings = embedder.embed_texts([query_text])
    if not query_embeddings:
        return ""

    # 使用原生 query 接口，按 story_id 过滤
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=top_k,
        where={"story_id": story_key}, # 核心优化：利用元数据过滤
        include=["documents", "metadatas", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return ""

    parts = []
    for idx, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
        # 距离转换为相似度分数 (Chroma 默认使用 L2 或余弦距离)
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

def persist_generated_role_slice(
    role_id: str,
    story_id: str,
    run_id: int,
    chapter_timestamp: str,
    topic: str,
    style: str,
    content: str,
) -> Path:
    """持久化生成的记忆切片。"""
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
