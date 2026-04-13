from __future__ import annotations

from importlib import import_module
import re


def _build_load_error(model_name_or_path: str, exc: Exception) -> RuntimeError:
    return RuntimeError(
        "Failed to load local seq2seq summary model "
        f"'{model_name_or_path}'. "
        "Please check model id and dependencies (transformers/torch). "
        f"Original error: {exc}"
    )


class HFSeq2SeqSummaryModel:
    """基于 HuggingFace Seq2Seq 的本地摘要模型（更适合小模型中文摘要尝试）。"""

    def __init__(
        self,
        model_name_or_path: str,
        max_new_tokens: int = 128,
        temperature: float = 0.2,
        device: str = "auto",
    ):
        if not model_name_or_path:
            raise ValueError("local.model_name_or_path 不能为空（hf_seq2seq 后端必须提供模型路径）")

        self.model_name_or_path = model_name_or_path
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        transformers = import_module("transformers")
        torch = import_module("torch")

        AutoTokenizer = getattr(transformers, "AutoTokenizer")
        AutoModelForSeq2SeqLM = getattr(transformers, "AutoModelForSeq2SeqLM")

        try:
            # 优先使用 fast tokenizer；失败后回退 slow tokenizer
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name_or_path,
                    use_fast=True,
                    trust_remote_code=True,
                )
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name_or_path,
                    use_fast=False,
                    trust_remote_code=True,
                )

            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name_or_path,
                trust_remote_code=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise _build_load_error(self.model_name_or_path, exc) from exc

        resolved_device = self._resolve_device(torch, device)
        self.device = resolved_device
        if resolved_device != "cpu":
            self.model = self.model.to(resolved_device)

    @staticmethod
    def _resolve_device(torch, device: str) -> str:
        if device != "auto":
            return device
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @staticmethod
    def _postprocess_text(text: str) -> str:
        # 去除中文字符之间的异常空格（如“会 议 纪 要”）
        text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
        # 去除中文标点前后的多余空格
        text = re.sub(r"\s+([，。！？；：])", r"\1", text)
        text = re.sub(r"([（【《])\s+", r"\1", text)
        text = re.sub(r"\s+([）】》])", r"\1", text)
        # 规整多空格
        text = re.sub(r"[ \t]{2,}", " ", text)

        # 去掉常见提示词回声前缀
        noise_prefixes = [
            "你是一个会议助手",
            "请基于下面的多人短对话输出中文摘要",
            "请直接输出最终摘要",
            "会议对话如下",
            "【会议对话】",
        ]
        for p in noise_prefixes:
            if text.startswith(p):
                text = text[len(p):].strip("：: \n")

        # 若模型回写了标题，尽量截取“会议纪要/摘要”后的正文
        for marker in ["【会议纪要】", "会议纪要：", "会议纪要:", "摘要：", "摘要:"]:
            if marker in text:
                text = text.split(marker, 1)[-1].strip()

        return text.strip()

    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        # 一些 Seq2Seq 模型（如 BART）不接受 token_type_ids，需在 generate 前移除
        inputs.pop("token_type_ids", None)
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            num_beams=4,
            length_penalty=1.0,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2,
            encoder_no_repeat_ngram_size=4,
            early_stopping=True,
        )
        raw = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        return self._postprocess_text(raw)
