from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeSettings:
    model_name_or_path: str
    max_input_tokens: int = 1024
    max_output_tokens: int = 256
    device: str = "auto"


class ColabSummaryRuntime:
    """Model runtime is isolated from API routing so loading/inference logic is not duplicated."""

    def __init__(self, settings: RuntimeSettings):
        self.settings = settings
        self.model_name = settings.model_name_or_path
        self._tokenizer = None
        self._model = None
        self._device = "cpu"

    def is_ready(self) -> bool:
        return self._tokenizer is not None and self._model is not None

    def load_model(self) -> None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch

        self._tokenizer = AutoTokenizer.from_pretrained(self.settings.model_name_or_path)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self.settings.model_name_or_path)

        requested = self.settings.device.strip().lower()
        if requested == "auto":
            if torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
        else:
            self._device = requested

        if self._device != "cpu":
            self._model = self._model.to(self._device)

    def summarize(self, text: str) -> str:
        if not self.is_ready():
            raise RuntimeError("model runtime is not ready")

        clean_text = (text or "").strip()
        if not clean_text:
            return ""

        encoded = self._tokenizer(
            clean_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.settings.max_input_tokens,
        )
        encoded.pop("token_type_ids", None)
        if self._device != "cpu":
            encoded = {k: v.to(self._device) for k, v in encoded.items()}

        output = self._model.generate(
            **encoded,
            max_new_tokens=self.settings.max_output_tokens,
            do_sample=False,
            num_beams=4,
            early_stopping=True,
        )
        return self._tokenizer.decode(output[0], skip_special_tokens=True).strip()
