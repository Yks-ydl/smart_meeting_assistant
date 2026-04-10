from __future__ import annotations

from typing import List


class TextChunker:
    """文本切分器（按语义边界切分）。"""

    def __init__(self, min_chunk_size: int = 3, max_chunk_size: int = 20):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str) -> List[str]:
        """将文本切分为语义单元（占位）。"""
        if not text:
            return []
        return [text]

    def merge(self, chunks: List[str]) -> str:
        """合并短片段（占位）。"""
        return " ".join(c for c in chunks if c)
