"""统一的 Markdown 工具函数。

合并自:
  - metadata_extractor._parse_front_matter
  - chroma_memory._parse_header
"""

from typing import Dict


def parse_markdown_header(text: str, max_guess_lines: int = 15) -> Dict[str, str]:
    """解析 Markdown 文件头部的 Key: Value 格式元数据。

    支持:
      - YAML 风格 front matter（--- 包裹）
      - 旧格式：前 N 行的 Key: Value 对

    Key 统一转为小写、空格替换为下划线。
    """
    metadata: Dict[str, str] = {}
    lines = text.splitlines()
    header_lines: list[str] = []

    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            header_lines.append(line)
    else:
        header_lines = lines[:max_guess_lines]

    for line in header_lines:
        if ":" in line:
            key, _, val = line.partition(":")
            metadata[key.strip().lower().replace(" ", "_")] = val.strip()

    return metadata
