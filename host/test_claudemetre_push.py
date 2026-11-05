"""Tests de claudemetre_push : uv run --no-project --with pytest pytest host/"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import claudemetre_push as cp

SCRIPT = Path(__file__).with_name("claudemetre_push.py")
WEBHOOK_ID = "test-webhook"
USAGE = {
    "five_hour": {"utilization": 24.0, "resets_at": "2026-10-28T14:29:59.997686+00:00"},
    "seven_day": {"utilization": 12.0, "resets_at": "2026-11-03T22:59:59.997709+00:00"},
    "seven_day_opus": None,
}


# --- normalisation -----------------------------------------------------------

def test_normalize_rounds_reset_to_the_second():
    body = cp.normalize(USAGE, 1793183889.7)
    assert body == {
        "five_hour": {"used_percentage": 24, "resets_at": 1793197800},   # 14:30:00 Z
        "seven_day": {"used_percentage": 12, "resets_at": 1793746800},   # 23:00:00 Z
        "measured_at": 1793183889,
        "source": "oauth",
    }


def test_normalize_unknown_and_not_started_windows():
    usage = {"five_hour": {"utilization": 0.0, "resets_at": None}, "seven_day": None}
    body = cp.normalize(usage, 0)
    assert body["five_hour"] == {"used_percentage": 0, "resets_at": None}
    assert body["seven_day"] is None
    assert cp.normalize({}, 0)["five_hour"] is None


def test_normalize_keeps_one_decimal():
    usage = {"five_hour": {"utilization": 23.46, "resets_at": None}}
    assert cp.normalize(usage, 0)["five_hour"]["used_percentage"] == 23.5


# --- espacement et attente ---------------------------------------------------

def test_schedule_spaces_calls_and_keeps_one_catch_up():
    state = {}
    assert cp.schedule(state, 1000) == "fetch"
    assert cp.schedule(state, 1010) == "wait"
    assert state["pending_until"] == 1000 + cp.MIN_INTERVAL
    assert cp.schedule(state, 1020) == "skip"
    assert cp.resume(state, 1120) == "fetch"
    assert "pending_until" not in state
    assert cp.schedule(state, 1240) == "fetch"


def test_backoff_grows_then_resets():
    state = {}
    waits = []
    for _ in range(4):
        cp.record_result(state, 429, None, 0)
        waits.append(state["backoff_until"])
    assert waits == [600, 1200, 1800, 1800]
    cp.record_result(state, 429, 3600, 0)
    assert state["backoff_until"] == 3600  # retry-after plus long : respecté
    assert cp.schedule(state, 100) == "skip"
    cp.record_result(state, 200, None, 0)
    assert "backoff_until" not in state and "backoff_step" not in state


# --- de bout en bout, avec un faux endpoint et un faux Home Assistant --------

class FakeServer:
    def __init__(self):
        self.usage_status = 200
        self.retry_after = None
        self.gets, self.posts = [], []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                server.gets.append(self.headers)  # noms d'en-têtes insensibles à la casse
                self.send_response(server.usage_status)
                if server.retry_after:
                    self.send_header("Retry-After", str(server.retry_after))
                self.end_headers()
                if server.usage_status == 200:
                    self.wfile.write(json.dumps(USAGE).encode())

            def do_POST(self):
                length = int(self.headers["Content-Length"])
                server.posts.append((self.path, json.loads(self.rfile.read(length))))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()


@pytest.fixture
def env(tmp_path, monkeypatch):
    server = FakeServer()
    config = tmp_path / "env"
    config.write_text(f"CLAUDEMETRE_HA_URL={server.url}\nCLAUDEMETRE_WEBHOOK_ID={WEBHOOK_ID}\n")
    creds = tmp_path / ".credentials.json"
    creds.write_text(json.dumps({"claudeAiOauth": {
        "accessToken": "secret-token", "expiresAt": (time.time() + 3600) * 1000}}))
    monkeypatch.setattr(cp, "USAGE_URL", f"{server.url}/api/oauth/usage")
    monkeypatch.setattr(cp, "CONFIG_FILE", config)
    monkeypatch.setattr(cp, "CREDENTIALS_FILE", creds)
    monkeypatch.setattr(cp, "CACHE_DIR", tmp_path / "cache")
    yield server, creds, tmp_path
    server.httpd.shutdown()


def test_run_reads_usage_and_pushes_to_ha(env):
    server, _, tmp_path = env
    cp.run()
    assert len(server.gets) == 1
    assert server.gets[0]["Authorization"] == "Bearer secret-token"
    assert server.gets[0]["anthropic-beta"] == "oauth-2025-04-20"
    path, body = server.posts[0]
    assert path == f"/api/webhook/{WEBHOOK_ID}"
    assert body["five_hour"] == {"used_percentage": 24, "resets_at": 1793197800}
    assert "secret-token" not in (tmp_path / "cache" / "log").read_text()


def test_run_burst_gives_one_catch_up_call(env, monkeypatch):
    server, _, _ = env
    monkeypatch.setattr(cp.time, "sleep", lambda s: None)
    cp.run()
    cp.run()  # trop tôt : attend la fin de l'intervalle, puis rattrape
    assert len(server.gets) == 2
    with cp.locked_state() as state:
        state["pending_until"] = time.time() + 60
    cp.run()  # un rattrapage est déjà programmé : rien
    assert len(server.gets) == 2


def test_run_429_waits_and_does_not_push(env):
    server, _, _ = env
    server.usage_status, server.retry_after = 429, 900
    cp.run()
    assert server.posts == []
    with cp.locked_state() as state:
        assert state["backoff_until"] - state["last_fetch"] == pytest.approx(900, abs=1)


def test_run_expired_token_makes_no_call(env):
    server, creds, _ = env
    creds.write_text(json.dumps({"claudeAiOauth": {
        "accessToken": "secret-token", "expiresAt": (time.time() - 10) * 1000}}))
    before = creds.read_text()
    cp.run()
    assert server.gets == [] and server.posts == []
    assert creds.read_text() == before  # jamais réécrit


# --- mode hook ---------------------------------------------------------------

def test_hook_mode_returns_at_once_with_empty_stdout(tmp_path):
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "config"),
           "XDG_CACHE_HOME": str(tmp_path / "cache"), "CLAUDE_CONFIG_DIR": str(tmp_path / "claude")}
    payload = json.dumps({"hook_event_name": "post_llm_call", "extra": {"x": "y" * 100_000}})
    start = time.monotonic()
    result = subprocess.run([sys.executable, str(SCRIPT)], input=payload.encode(),
                            capture_output=True, env=env, timeout=5)
    assert time.monotonic() - start < 1
    assert result.returncode == 0
    assert result.stdout == b"" and result.stderr == b""
    log = tmp_path / "cache" / "claudemetre" / "log"
    for _ in range(50):  # le processus détaché note la config manquante
        if log.exists():
            break
        time.sleep(0.05)
    assert "configuration incomplète" in log.read_text()
