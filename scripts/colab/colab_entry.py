from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

try:
    from .colab_summary_service import create_app
    from .colab_tunnel import start_ngrok_tunnel
except ImportError:
    # Allow direct script execution: `python scripts/colab/colab_entry.py`.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.colab.colab_summary_service import create_app
    from scripts.colab.colab_tunnel import start_ngrok_tunnel


def _resolve_public_url(port: int) -> str:
    """Reuse an existing notebook tunnel when provided to avoid duplicated ngrok endpoints."""
    existing_public_url = os.getenv("COLAB_PUBLIC_URL", "").strip()
    if existing_public_url:
        cleaned_url = existing_public_url.rstrip("/")
        print(f"[ColabEntry] using existing ngrok tunnel: {cleaned_url}")
        return cleaned_url
    return start_ngrok_tunnel(port)


def main() -> None:
    # Keep startup sequencing explicit so Colab users can see each stage progress in notebook output.
    host = os.getenv("COLAB_SUMMARY_HOST", "0.0.0.0")
    port = int(os.getenv("COLAB_SUMMARY_PORT", "8002"))

    print("[ColabEntry] creating app and loading model...")
    app = create_app()
    public_url = _resolve_public_url(port)
    print(f"[ColabEntry] set SUMMARY_SERVICE_URL to: {public_url}/api/v1/summary/generate")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
