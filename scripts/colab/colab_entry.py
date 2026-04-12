from __future__ import annotations

import os

import uvicorn

from .colab_summary_service import create_app
from .colab_tunnel import start_ngrok_tunnel


def main() -> None:
    # Keep startup sequencing explicit so Colab users can see each stage progress in notebook output.
    host = os.getenv("COLAB_SUMMARY_HOST", "0.0.0.0")
    port = int(os.getenv("COLAB_SUMMARY_PORT", "8002"))

    print("[ColabEntry] creating app and loading model...")
    app = create_app()
    public_url = start_ngrok_tunnel(port)
    print(f"[ColabEntry] set SUMMARY_SERVICE_URL to: {public_url}/api/v1/summary/generate")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
