from __future__ import annotations

from .base import LocalSummaryModel
from .hf_causal import HFCausalSummaryModel
from .hf_seq2seq import HFSeq2SeqSummaryModel
from .mock_model import MockLocalSummaryModel


def build_local_summary_model(
    backend: str = "mock",
    model_name_or_path: str = "",
    max_new_tokens: int = 256,
    temperature: float = 0.2,
    device: str = "auto",
) -> LocalSummaryModel:
    backend_key = backend.lower().strip()
    if backend_key == "hf_seq2seq":
        return HFSeq2SeqSummaryModel(
            model_name_or_path=model_name_or_path,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            device=device,
        )
    if backend_key == "hf_causal":
        return HFCausalSummaryModel(
            model_name_or_path=model_name_or_path,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            device=device,
        )
    if backend_key == "mock":
        return MockLocalSummaryModel()
    raise ValueError(
        f"Unsupported local backend: {backend}. Expected 'mock', 'hf_seq2seq' or 'hf_causal'."
    )
