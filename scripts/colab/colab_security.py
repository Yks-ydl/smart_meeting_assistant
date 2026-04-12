from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException


@dataclass
class AuthSettings:
    auth_enabled: bool = True
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    auth_token: str = ""


def validate_auth_header(header_value: str | None, settings: AuthSettings) -> None:
    """Centralize auth verification to avoid duplicated route-level token checks."""
    if not settings.auth_enabled:
        return

    if not settings.auth_token:
        raise HTTPException(status_code=500, detail="auth token is not configured")

    expected = (
        f"{settings.auth_scheme} {settings.auth_token}".strip()
        if settings.auth_scheme
        else settings.auth_token
    )
    received = (header_value or "").strip()
    if received != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
