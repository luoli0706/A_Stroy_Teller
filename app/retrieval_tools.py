import re
import os
import asyncio
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.metadata_store import query_metadata
from app.rag.ollama_embedding import OllamaEmbeddingClient
from app.config import RAG_TOP_K
import chromadb
from app.config import CHROMA_DIR, RAG_COLLECTION_NAME

def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=RAG_COLLECTION_NAME)

def grep_content(pattern: str, candidate_paths: List[str], context_lines: int = 2) -> List[Dict[str, Any]]:
    """
    在候选文件中进行正则搜索，返回匹配行及其上下文。
    """
    results = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return []
    
    for path_str in candidate_paths:
        path = Path(path_str)
        if not path.exists():
            continue
            
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                if regex.search(line):
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    results.append({
                        "path": path_str,
                        "line_no": i + 1,
                        "content": line.strip(),
                        "context": "\n".join(lines[start:end]),
                        "score": 0.8  # Grep matches get a baseline score
                    })
        except Exception as e:
            print(f"Error reading {path_str} during grep: {e}")
            
    return results

def smart_read(path: str, byte_start: int = 0, byte_end: Optional[int] = None, mode: str = "evidence_first") -> str:
    """
    智能读取文件片段。
    """
    p = Path(path)
    if not p.exists():
        return f"Error: File {path} not found."
        
    try:
        with open(p, "rb") as f:
            f.seek(byte_start)
            if byte_end and byte_end > byte_start:
                content_bytes = f.read(byte_end - byte_start)
            else:
                content_bytes = f.read(2000) # Default limit
            
            text = content_bytes.decode("utf-8", errors="replace")
            
            if mode == "evidence_first":
                # 简单清洗，避免 front matter 干扰
                display_text = text
                if "---" in text[:200]:
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        display_text = parts[2].strip()

                return (
                    f"--- Source: {p.name} (Bytes {byte_start}-{byte_end or '...'}) ---\n"
                    f"{display_text.strip()}\n"
                    f"--- End of Citation ---"
                )
            return text
    except Exception as e:
        return f"Error reading {path}: {e}"

def hybrid_search(story_id: str, query: str, filters: Dict[str, Any] = None, limit: int = 5) -> str:
    """
    混合检索主函数：并行执行向量检索与 SQL 元数据筛选，并进行融合。
    """
    # 1. 向量检索 (Semantic)
    embedder = OllamaEmbeddingClient()
    query_embeddings = embedder.embed_texts([query])
    vector_results = []
    if query_embeddings:
        collection = _get_collection()
        # 转换 story_id 为 normalized 格式
        story_key = story_id.strip().replace(" ", "_")
        
        # 构造 Chroma filter
        conditions = [{"story_id": story_key}]
        if filters and "role_id" in filters:
            role_val = filters["role_id"]
            if isinstance(role_val, list):
                conditions.append({"source_role": {"$in": role_val}})
            else:
                conditions.append({"source_role": role_val})
        
        where_filter = conditions[0] if len(conditions) == 1 else {"$and": conditions}

        try:
            res = collection.query(
                query_embeddings=query_embeddings,
                n_results=limit * 2,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            
            for doc, meta, dist in zip(docs, metas, dists):
                vector_results.append({
                    "content": doc,
                    "metadata": meta,
                    "score": 1.0 - dist if dist < 1.0 else 0.1,
                    "source": "vector"
                })
        except Exception as e:
            print(f"Vector search failed: {e}")

    # 2. SQL 元数据检索 (Structured)
    sql_filters = {"story_id": story_id.strip().replace(" ", "_")}
    if filters:
        sql_filters.update(filters)
    
    sql_chunks = query_metadata(sql_filters, limit=limit)
    
    # 3. 融合与去重
    # 优先保证 SQL 精准匹配，同时补充向量相似内容
    final_items = []
    seen_sources = set()

    # 先放 SQL 结果
    for chunk in sql_chunks:
        # 构造一个唯一的 key 来去重，比如 source_path + start_offset
        key = f"{chunk['source_path']}@{chunk['byte_offset_start']}"
        if key not in seen_sources:
            final_items.append({
                "path": chunk["source_path"],
                "start": chunk["byte_offset_start"],
                "end": chunk["byte_offset_end"],
                "score": 1.0, # SQL 精准匹配给满分
                "summary": chunk.get("summary", "")
            })
            seen_sources.add(key)

    # 补充向量结果中尚未包含的部分
    for vr in vector_results:
        # Chroma 存储的是 slice_id，我们需要对应到文件和偏移
        # 这里的映射目前比较粗糙，后期可以优化
        # 简单起见，如果向量分值很高且 SQL 没搜到，则加入
        if vr["score"] > 0.7:
            # 这里的 vector result 目前缺少具体的 byte offset，
            # 我们直接使用它的文本，或者通过 slice_id 寻找文件。
            # 暂时直接添加其文本内容
            final_items.append({
                "text_content": vr["content"],
                "score": vr["score"],
                "label": f"Semantic (Score: {vr['score']:.2f})"
            })

    if not final_items:
        return "No relevant memories found."

    # 4. 读取并格式化
    output = []
    for item in sorted(final_items, key=lambda x: x["score"], reverse=True)[:limit]:
        if "path" in item:
            content = smart_read(item["path"], item["start"], item["end"])
            output.append(content)
        elif "text_content" in item:
            output.append(f"--- {item['label']} ---\n{item['text_content']}\n--- End Citation ---")
            
    return "\n\n".join(output)

async def hybrid_search_async(story_id: str, query: str, filters: Dict[str, Any] = None, limit: int = 5) -> str:
    """异步包装。"""
    return await asyncio.to_thread(hybrid_search, story_id, query, filters, limit)
