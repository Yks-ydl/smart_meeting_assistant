from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from time import time
from typing import Any, Optional


@dataclass
class BufferedItem:
    data: Any
    timestamp: float


class AsyncCircularBuffer:
    """异步环形缓冲区（支持超时丢弃）。"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer: deque[BufferedItem] = deque(maxlen=capacity)
        self.condition = asyncio.Condition()

    async def put(self, item: Any) -> None:
        """放入数据。"""
        async with self.condition:
            self.buffer.append(BufferedItem(item, time()))
            self.condition.notify()

    async def get(self, timeout: Optional[float] = None) -> Any:
        """取出数据（支持超时）。"""
        async with self.condition:
            if not self.buffer:
                await asyncio.wait_for(self.condition.wait(), timeout=timeout)
            return self.buffer.popleft().data if self.buffer else None

    def flush(self) -> list[Any]:
        """清空缓冲区并返回所有数据。"""
        items = [item.data for item in self.buffer]
        self.buffer.clear()
        return items
