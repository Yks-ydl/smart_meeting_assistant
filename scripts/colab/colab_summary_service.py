from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import FastAPI, Request
from pydantic import BaseModel

from .colab_model_runtime import ColabSummaryRuntime, RuntimeSettings
from .colab_security import AuthSettings, validate_auth_header


class MeetingContent(BaseModel):
    session_id: str
    text: str


@dataclass
class ColabServiceSettings:
    auth_enabled: bool = True
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    auth_token: str = ""


def create_app(
    runtime: ColabSummaryRuntime | object | None = None,
    settings: ColabServiceSettings | None = None,
) -> FastAPI:
    # Build the app through a factory so tests can inject fake runtimes without loading heavy models.
    app = FastAPI(title="Colab Summary Inference Service", version="1.0.0")

    service_settings = settings or ColabServiceSettings(
        auth_enabled=os.getenv("COLAB_SUMMARY_AUTH_ENABLED", "true").strip().lower() != "false",
        auth_header=os.getenv("COLAB_SUMMARY_AUTH_HEADER", "Authorization"),
        auth_scheme=os.getenv("COLAB_SUMMARY_AUTH_SCHEME", "Bearer"),
        auth_token=os.getenv("COLAB_SUMMARY_AUTH_TOKEN", ""),
    )

    service_runtime = runtime
    if service_runtime is None:
        model_name = os.getenv("SUMMARY_MODEL", "fnlp/bart-base-chinese")
        max_input_tokens = int(os.getenv("SUMMARY_MAX_INPUT_TOKENS", "1024"))
        max_output_tokens = int(os.getenv("SUMMARY_MAX_OUTPUT_TOKENS", "256"))
        device = os.getenv("SUMMARY_DEVICE", "auto")

        service_runtime = ColabSummaryRuntime(
            RuntimeSettings(
                model_name_or_path=model_name,
                max_input_tokens=max_input_tokens,
                max_output_tokens=max_output_tokens,
                device=device,
            )
        )
        service_runtime.load_model()

    auth_settings = AuthSettings(
        auth_enabled=service_settings.auth_enabled,
        auth_header=service_settings.auth_header,
        auth_scheme=service_settings.auth_scheme,
        auth_token=service_settings.auth_token,
    )

    @app.post("/api/v1/summary/generate")
    async def generate_summary(content: MeetingContent, request: Request):
        header_value = request.headers.get(auth_settings.auth_header.lower())
        validate_auth_header(header_value=header_value, settings=auth_settings)

        summary = service_runtime.summarize(content.text)
        return {
            "status": "success",
            "session_id": content.session_id,
            "summary": summary,
            "mode": "colab_remote",
        }

    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "model_loaded": bool(service_runtime.is_ready()),
            "model_name": getattr(service_runtime, "model_name", "unknown"),
        }

    return app
