from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


TextHook = Callable[[str], str]


@dataclass
class TranslationTuningChannel:
    """内部调优通道。

    用于你在不改外部调用方式的前提下，快速插入前后处理逻辑。
    """

    pre_hooks: list[TextHook] = field(default_factory=list)
    post_hooks: list[TextHook] = field(default_factory=list)

    def apply_pre(self, text: str) -> str:
        result = text
        for hook in self.pre_hooks:
            result = hook(result)
        return result

    def apply_post(self, text: str) -> str:
        result = text
        for hook in self.post_hooks:
            result = hook(result)
        return result
