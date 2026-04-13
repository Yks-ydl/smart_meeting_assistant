from __future__ import annotations

import os


def start_ngrok_tunnel(local_port: int) -> str:
    """Use a dedicated helper for tunnel startup to keep entry orchestration and tunnel logic decoupled."""
    from pyngrok import ngrok

    auth_token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    if auth_token:
        ngrok.set_auth_token(auth_token)

    # Reuse existing local agent tunnel first to avoid creating duplicate endpoints.
    existing_tunnels = ngrok.get_tunnels()
    if existing_tunnels:
        for tunnel in existing_tunnels:
            public_url = getattr(tunnel, "public_url", "")
            if public_url:
                print(f"[ColabTunnel] reusing existing tunnel: {public_url}")
                return public_url

    tunnel = ngrok.connect(local_port, "http")
    public_url = tunnel.public_url
    print(f"[ColabTunnel] public url: {public_url}")
    return public_url
