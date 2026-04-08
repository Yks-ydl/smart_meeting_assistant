from __future__ import annotations


class MockLocalSummaryModel:
    """开发用本地模型占位实现。

    说明：这是本地推理链路的 mock，不是规则摘要。
    仅用于在未部署真实本地模型前打通接口。
    """

    def generate(self, prompt: str) -> str:
        preview = prompt.replace("\n", " ")[:220]
        return f"[local-model-mock] {preview}"
