from __future__ import annotations

from importlib import import_module
from typing import Any


class HFCausalSummaryModel:
    """基于 HuggingFace CausalLM 的本地摘要模型。"""

    def __init__(
        self,
        model_name_or_path: str,
        max_new_tokens: int = 256,
        temperature: float = 0.2,
        device: str = "auto",
    ):
        if not model_name_or_path:
            raise ValueError("local.model_name_or_path 不能为空（hf_causal 后端必须提供模型路径）")

        self.model_name_or_path = model_name_or_path
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.device = device

        transformers = import_module("transformers")
        torch = import_module("torch")

        AutoTokenizer = getattr(transformers, "AutoTokenizer")
        AutoModelForCausalLM = getattr(transformers, "AutoModelForCausalLM")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path, trust_remote_code=True)

        torch_dtype: Any = getattr(torch, "float16") if self.device != "cpu" else getattr(torch, "float32")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name_or_path,
            trust_remote_code=True,
            torch_dtype=torch_dtype,
        )

        if self.device == "cpu":
            self.model = self.model.to("cpu")
        elif self.device not in {"auto", "cpu"}:
            self.model = self.model.to(self.device)

    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=True,
            temperature=self.temperature,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        if text.startswith(prompt):
            text = text[len(prompt):].strip()
        return text.strip()
