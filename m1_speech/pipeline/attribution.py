from __future__ import annotations

import re

from m1_speech.utils.config import SpeakerConfig
from m1_speech.utils.schemas import AudioSource


class ChannelSpeakerAttributor:
    """基于独立 channel_id / user_id 直接赋予 speaker label。"""

    def __init__(self, config: SpeakerConfig) -> None:
        self.config = config

    def assign_labels(self, sources: list[AudioSource]) -> dict[str, str]:
        """为每个音轨生成稳定的说话人标签。"""

        label_map: dict[str, str] = {}
        for index, source in enumerate(sources):
            label_map[source.source_id] = self._build_label(source.source_id, index)
        return label_map

    def _build_label(self, source_id: str, index: int) -> str:
        """根据配置决定保留原始 ID，还是改成匿名标签。"""

        if self.config.label_mode == "anonymous":
            return f"{self.config.anonymous_prefix}_{self._index_to_token(index)}"
        if self.config.label_mode == "regex_name":
            extracted = self._extract_name_from_source(source_id)
            if extracted is not None:
                return extracted
            if self.config.fallback_mode == "anonymous":
                return f"{self.config.anonymous_prefix}_{self._index_to_token(index)}"
        return source_id

    def _extract_name_from_source(self, source_id: str) -> str | None:
        """使用正则表达式从 source_id 中提取 speaker 名字。"""

        matched = re.match(self.config.name_pattern, source_id)
        if matched is None:
            return None
        extracted = matched.group(1).strip()
        return extracted or None

    @staticmethod
    def _index_to_token(index: int) -> str:
        """将序号转换成 A, B, ..., Z, AA, AB 形式的标签后缀。"""

        value = index + 1
        token = []
        while value > 0:
            value, remainder = divmod(value - 1, 26)
            token.append(chr(ord("A") + remainder))
        return "".join(reversed(token))
