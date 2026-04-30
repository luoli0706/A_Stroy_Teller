import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any
import json

from app.markdown_utils import parse_markdown_header

PARSER_VERSION = "v1.0"

def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_chunks_from_markdown(file_path: Path) -> List[Dict[str, Any]]:
    """从 Markdown 文件中提取分块及其元数据。"""
    if not file_path.exists():
        return []
        
    full_text = file_path.read_text(encoding="utf-8")
    file_metadata = parse_markdown_header(full_text)
    
    # 移除 header 部分以精确定位字节偏移
    body_text = full_text
    header_match = re.match(r'^---\n(.*?)\n---\n', full_text, re.DOTALL)
    if header_match:
        header_len = len(header_match.group(0).encode("utf-8"))
        body_text = full_text[len(header_match.group(0)):]
        start_offset = header_len
    else:
        # 猜测旧格式的分隔符
        divider = "---\n"
        if divider in full_text:
            parts = full_text.split(divider, 1)
            start_offset = len((parts[0] + divider).encode("utf-8"))
            body_text = parts[1]
        else:
            start_offset = 0
            body_text = full_text

    chunks = []
    # 改进的分块正则：匹配 ## Chapter 或 ### 级别的标题
    # 我们保留标题作为块的开头
    pattern = r'(?m)^(#+ .+)$'
    matches = list(re.finditer(pattern, body_text))
    
    if not matches:
        # 如果没有标题，整体作为一个 chunk
        raw_chunks = [(0, len(body_text), body_text)]
    else:
        raw_chunks = []
        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i+1].start() if i+1 < len(matches) else len(body_text)
            chunk_content = body_text[start:end].strip()
            if chunk_content:
                raw_chunks.append((start, end, chunk_content))

    for idx, (c_start, c_end, content) in enumerate(raw_chunks):
        chunk_hash = _compute_hash(content)
        
        rid = file_metadata.get("role_id", "unknown")
        sid = file_metadata.get("story_id", "unknown")
        
        # [v0.3.0] 组合 ID 确保全局唯一：故事ID + 角色ID + 文件名 + 块序号
        chunk_id = f"{sid}_{rid}_{file_path.stem}_ch{idx}"
        
        # 尝试从第一行标题提取 chapter_id
        lines = content.splitlines()
        first_line = lines[0] if lines else ""
        chapter_id_match = re.search(r'Chapter (\d+)', first_line, re.I)
        chapter_id = chapter_id_match.group(1) if chapter_id_match else (file_metadata.get("chapter_timestamp") or f"idx_{idx}")

        chunk_data = {
            "chunk_id": chunk_id,
            "role_id": file_metadata.get("role_id", "unknown"),
            "story_id": file_metadata.get("story_id", "unknown"),
            "run_id": file_metadata.get("run_id", "0"),
            "chapter_id": chapter_id,
            "scene_id": f"scene_{idx}",
            "time_anchor": file_metadata.get("chapter_timestamp"),
            "location": file_metadata.get("location", "unknown"),
            "entities": [], 
            "props": [],    
            "narrative_type": file_metadata.get("narrative_type", "fact"),
            "summary": content[:300].replace("\n", " ") + "...",
            "source_path": str(file_path),
            "byte_offset_start": start_offset + c_start,
            "byte_offset_end": start_offset + c_end,
            "content_hash": chunk_hash,
            "parser_version": PARSER_VERSION
        }
        chunks.append(chunk_data)
        
    return chunks
