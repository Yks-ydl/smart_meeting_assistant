from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

from scripts.colab.colab_tunnel import start_ngrok_tunnel


class _FakeTunnel:
    def __init__(self, public_url: str):
        self.public_url = public_url


class _FakeNgrok:
    # Keep ngrok behavior in one fake object so tunnel tests do not need the real binary/runtime.
    def __init__(self, tunnels: list[_FakeTunnel] | None = None, connect_url: str = "https://new.example.ngrok-free.app"):
        self._tunnels = tunnels or []
        self._connect_url = connect_url
        self.auth_token = ""
        self.connect_called = 0
        self.connect_args: tuple[int, str] | None = None

    def set_auth_token(self, token: str) -> None:
        self.auth_token = token

    def get_tunnels(self):
        return self._tunnels

    def connect(self, local_port: int, proto: str):
        self.connect_called += 1
        self.connect_args = (local_port, proto)
        return _FakeTunnel(self._connect_url)


class ColabTunnelTest(unittest.TestCase):
    def test_reuses_existing_tunnel_before_connecting(self) -> None:
        fake_ngrok = _FakeNgrok(tunnels=[_FakeTunnel("https://existing.example.ngrok-free.app")])
        fake_pyngrok = types.ModuleType("pyngrok")
        fake_pyngrok.ngrok = fake_ngrok

        with patch.dict(sys.modules, {"pyngrok": fake_pyngrok}):
            with patch.dict(os.environ, {"NGROK_AUTHTOKEN": "token-123"}, clear=False):
                public_url = start_ngrok_tunnel(local_port=8002)

        self.assertEqual(public_url, "https://existing.example.ngrok-free.app")
        self.assertEqual(fake_ngrok.auth_token, "token-123")
        self.assertEqual(fake_ngrok.connect_called, 0)

    def test_creates_tunnel_when_none_exists(self) -> None:
        fake_ngrok = _FakeNgrok(tunnels=[], connect_url="https://new.example.ngrok-free.app")
        fake_pyngrok = types.ModuleType("pyngrok")
        fake_pyngrok.ngrok = fake_ngrok

        with patch.dict(sys.modules, {"pyngrok": fake_pyngrok}):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("NGROK_AUTHTOKEN", None)
                public_url = start_ngrok_tunnel(local_port=8002)

        self.assertEqual(public_url, "https://new.example.ngrok-free.app")
        self.assertEqual(fake_ngrok.connect_called, 1)
        self.assertEqual(fake_ngrok.connect_args, (8002, "http"))


if __name__ == "__main__":
    unittest.main()
