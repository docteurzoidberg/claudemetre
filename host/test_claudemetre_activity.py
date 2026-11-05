"""Tests de claudemetre_activity : uv run --no-project --with pytest pytest host/"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import claudemetre_activity as ca
import claudemetre_push as cp
from test_claudemetre_push import FakeServer

SCRIPT = Path(__file__).with_name("claudemetre_activity.py")
ME = (os.getpid(), ca.proc_stat(os.getpid())[2])  # un processus vivant


def cc(event, sid="s1", **fields):
    return {"hook_event_name": event, "session_id": sid,
            "transcript_path": f"/nonexistent/{sid}.jsonl", **fields}


def hm(event, sid="h1", **extra):
    return {"hook_event_name": event, "session_id": sid, "extra": extra}


def play(*payloads, entries=None, now=1000.0):
    entries = {} if entries is None else entries
    for p in payloads:
        ca.apply_event(entries, p, now, ME)
    return entries


# --- Claude Code -------------------------------------------------------------

def test_claude_code_turn():
    entries = play(cc("UserPromptSubmit"), cc("PostToolUse", tool_name="Bash"))
    assert ca.counts(entries) == (1, 0)
    play(cc("Stop"), entries=entries)
    assert entries == {}


def test_parallel_sessions_count_separately():
    entries = play(cc("UserPromptSubmit", "a"), cc("UserPromptSubmit", "b"))
    assert ca.counts(entries) == (2, 0)
    play(cc("StopFailure", "a"), entries=entries)
    assert ca.counts(entries) == (1, 0)


def test_background_subagent_outlives_main_stop():
    entries = play(cc("UserPromptSubmit"), cc("SubagentStart", agent_id="a1"), cc("Stop"))
    assert ca.counts(entries) == (1, 0)
    play(cc("PostToolUse", agent_id="a1", tool_name="Read"), entries=entries)
    assert list(entries) == ["cc:s1:a1"]
    play(cc("SubagentStop", agent_id="a1"), entries=entries)
    assert entries == {}


def test_session_end_drops_main_and_subagents():
    entries = play(cc("UserPromptSubmit"), cc("SubagentStart", agent_id="a1"),
                   cc("UserPromptSubmit", "other"), cc("SessionEnd", reason="clear"))
    assert list(entries) == ["cc:other"]


def test_permission_wait_ignores_other_parallel_tools():
    entries = play(cc("UserPromptSubmit"), cc("PermissionRequest", tool_name="Bash"))
    assert ca.counts(entries) == (0, 1)
    play(cc("PostToolUse", tool_name="Read"), entries=entries)
    assert ca.counts(entries) == (0, 1)
    play(cc("PostToolUse", tool_name="Bash"), entries=entries)
    assert ca.counts(entries) == (1, 0)
    play(cc("PermissionRequest", tool_name="Write"), cc("PermissionDenied", tool_name="Write"),
         entries=entries)
    assert ca.counts(entries) == (1, 0)


def test_question_and_elicitation_waits():
    entries = play(cc("UserPromptSubmit"), cc("PreToolUse", tool_name="AskUserQuestion"))
    assert ca.counts(entries) == (0, 1)
    play(cc("PostToolUse", tool_name="AskUserQuestion"), entries=entries)
    assert ca.counts(entries) == (1, 0)
    play(cc("Elicitation", mcp_server_name="m", elicitation_id="e1"), entries=entries)
    assert ca.counts(entries) == (0, 1)
    play(cc("ElicitationResult", mcp_server_name="m", elicitation_id="e1", action="accept"),
         entries=entries)
    assert ca.counts(entries) == (1, 0)


def test_new_prompt_clears_stale_waits():
    entries = play(cc("UserPromptSubmit"), cc("PermissionRequest", tool_name="Bash"),
                   cc("UserPromptSubmit"))
    assert ca.counts(entries) == (1, 0)


def test_interrupted_tool_ends_the_turn():
    entries = play(cc("UserPromptSubmit"),
                   cc("PostToolUseFailure", tool_name="Bash", is_interrupt=True))
    assert entries == {}


# --- Hermes ------------------------------------------------------------------

def test_hermes_turn_subagent_and_human_input():
    entries = play(hm("pre_llm_call"), hm("subagent_start", "h1", child_session_id="c1"))
    assert ca.counts(entries) == (2, 0)
    play(hm("on_human_input_request", "h1", kind="approval", request_id="r1"), entries=entries)
    assert ca.counts(entries) == (1, 1)
    play(hm("on_human_input_resolved", "", request_id="r1"),
         hm("subagent_stop", "h1", child_session_id="c1"), entries=entries)
    assert ca.counts(entries) == (1, 0)
    play(hm("on_session_end", "h1", completed=False, interrupted=True), entries=entries)
    assert entries == {}


def test_hermes_human_input_outside_a_known_turn():
    entries = play(hm("on_human_input_request", "", kind="sudo", request_id="r2"))
    assert ca.counts(entries) == (0, 1)
    play(hm("on_human_input_resolved", "", request_id="r2"), entries=entries)
    assert entries == {}


def test_hermes_compaction_renames_the_session():
    entries = play(hm("pre_llm_call", "old"), hm("post_compaction", "new", old_session_id="old"))
    play(hm("on_session_end", "new"), entries=entries)
    assert entries == {}


# --- fins non signalées ------------------------------------------------------

def test_prune_dead_process():
    entries = play(cc("UserPromptSubmit"))
    entries["cc:s1"]["start"] = -1  # même pid, autre processus
    assert ca.prune(entries, 1001) == [("cc:s1", "processus disparu")]


def write_transcript(path, when, *more):
    lines = [
        {"type": "assistant", "timestamp": "2026-10-29T10:00:00.000Z",
         "message": {"content": [{"type": "tool_use", "input": {"command": "grep '[Request interrupted by user'"}}]}},
        {"type": "user", "timestamp": when, "interruptedMessageId": "x",
         "message": {"role": "user", "content": [{"type": "text", "text": "[Request interrupted by user]"}]}},
        *more,
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))


def test_interrupt_quoted_in_a_tool_result_is_ignored(tmp_path):
    transcript = tmp_path / "t.jsonl"
    quoted = {"type": "user", "timestamp": "2026-10-29T10:05:00.000Z",
              "message": {"role": "user", "content": [{"type": "tool_result", "content":
                          '"text": "[Request interrupted by user for tool use]"'}]}}
    write_transcript(transcript, "2026-10-29T10:00:05.000Z", quoted)
    assert ca.read_transcript_tail(transcript)[0] == ca.to_epoch("2026-10-29T10:00:05.000Z")
    tool_use = {"type": "user", "timestamp": "2026-10-29T10:06:00.000Z",
                "message": {"role": "user", "content": [
                    {"type": "text", "text": "[Request interrupted by user for tool use]"}]}}
    write_transcript(transcript, "2026-10-29T10:00:05.000Z", quoted, tool_use)
    assert ca.read_transcript_tail(transcript)[0] == ca.to_epoch("2026-10-29T10:06:00.000Z")


def test_prune_interrupt_after_turn_start_only(tmp_path):
    transcript = tmp_path / "t.jsonl"
    write_transcript(transcript, "2026-10-29T10:00:05.000Z")
    marker = ca.to_epoch("2026-10-29T10:00:05.000Z")
    assert ca.read_transcript_tail(transcript)[0] == marker
    entries = {}
    for sid, since in (("before", marker - 10), ("after", marker + 1)):
        ca.apply_event(entries, cc("UserPromptSubmit", sid, transcript_path=str(transcript)), since, ME)
    assert ca.prune(entries, marker + 2) == [("cc:before", "interruption")]
    assert list(entries) == ["cc:after"]


def test_prune_turn_cancelled_before_the_first_word(tmp_path):
    """Échap pendant la réflexion : le transcript s'arrête sur la requête."""
    transcript = tmp_path / "t.jsonl"
    asked = ca.to_epoch("2026-10-29T10:00:01.000Z")
    lines = [
        {"type": "user", "timestamp": "2026-10-29T10:00:00.900Z",
         "message": {"role": "user", "content": "Écris un long poème"}},
        {"type": "attachment", "timestamp": "2026-10-29T10:00:00.950Z"},
        {"type": "api-request", "timestamp": "2026-10-29T10:00:01.000Z"},
        {"type": "last-prompt"},
    ]
    transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
    assert ca.read_transcript_tail(transcript) == (0, asked)
    entries = {}
    for event in (cc("UserPromptSubmit", transcript_path=str(transcript)),
                  cc("SubagentStart", agent_id="a1", transcript_path=str(transcript))):
        ca.apply_event(entries, event, asked - 1, ME)
    assert ca.prune(entries, asked + ca.UNANSWERED_AFTER - 1) == []
    assert ca.prune(entries, asked + ca.UNANSWERED_AFTER + 1) == [("cc:s1", "sans réponse du modèle")]
    assert list(entries) == ["cc:s1:a1"]  # un sous-agent n'est pas concerné

    lines.append({"type": "assistant", "timestamp": "2026-10-29T10:03:00.000Z",
                  "message": {"content": [{"type": "thinking", "thinking": ""}]}})
    transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
    assert ca.read_transcript_tail(transcript) == (0, 0)  # le modèle a répondu


def test_prune_stale_entries_but_not_waits():
    entries = play(cc("UserPromptSubmit", "a"), cc("UserPromptSubmit", "b"),
                   cc("PermissionRequest", "b", tool_name="Bash"))
    later = 1000 + ca.STALE_AFTER + 1
    assert ca.prune(entries, later) == [("cc:a", "sans nouvelles")]
    assert list(entries) == ["cc:b"]


def test_agent_process_skips_shells():
    code = "import claudemetre_activity as ca; print(ca.agent_process()[0])"
    out = subprocess.run(["bash", "-c", f"{sys.executable} -c '{code}'; true"],
                         capture_output=True, text=True, cwd=SCRIPT.parent, check=True)
    assert int(out.stdout) == os.getpid()


# --- envoi à Home Assistant --------------------------------------------------

@pytest.fixture
def ha(tmp_path, monkeypatch):
    server = FakeServer()
    config = tmp_path / "env"
    config.write_text(f"CLAUDEMETRE_HA_URL={server.url}\nCLAUDEMETRE_ACTIVITY_WEBHOOK_ID=act\n")
    monkeypatch.setattr(cp, "CONFIG_FILE", config)
    monkeypatch.setattr(cp, "CACHE_DIR", tmp_path / "cache")
    yield server
    server.httpd.shutdown()


def set_registry(*payloads):
    with ca.locked_registry() as entries:
        entries.clear()
        play(*payloads, entries=entries)


def test_publish_on_change_then_heartbeat(ha):
    set_registry(cc("UserPromptSubmit"))
    ca.publish(1000)
    assert ha.posts == [("/api/webhook/act",
                         {"active": 1, "attention": 0, "updated_at": 1000, "source": "hooks"})]
    ca.publish(1010)  # inchangé
    assert len(ha.posts) == 1
    ca.publish(1000 + ca.HEARTBEAT)  # toujours actif : renvoyé
    assert len(ha.posts) == 2
    set_registry()
    ca.publish(1000 + ca.HEARTBEAT + 1)
    assert ha.posts[-1][1]["active"] == 0
    ca.publish(1000 + 3 * ca.HEARTBEAT)  # tout à zéro : plus rien à renvoyer
    assert len(ha.posts) == 3


def test_publish_retries_after_failure(ha, monkeypatch):
    set_registry(hm("on_human_input_request", "h1", request_id="r1"))
    real_push = cp.push
    monkeypatch.setattr(cp, "push", lambda *a: None)  # HA injoignable
    ca.publish(1000)
    monkeypatch.setattr(cp, "push", real_push)
    ca.publish(1010)  # trop tôt pour réessayer
    assert ha.posts == []
    ca.publish(1000 + ca.HEARTBEAT)
    assert ha.posts[0][1]["attention"] == 1


# --- mode hook ---------------------------------------------------------------

def test_hook_mode_returns_at_once_with_empty_stdout(tmp_path):
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "config"),
           "XDG_CACHE_HOME": str(tmp_path / "cache")}
    payload = json.dumps(hm("pre_llm_call", "h1", conversation_history=["x" * 100_000]))
    start = time.monotonic()
    result = subprocess.run([sys.executable, str(SCRIPT)], input=payload.encode(),
                            capture_output=True, env=env, timeout=5)
    assert time.monotonic() - start < 1
    assert result.returncode == 0
    assert result.stdout == b"" and result.stderr == b""
    registry = json.loads((tmp_path / "cache" / "claudemetre" / "activity.json").read_text())
    assert registry["hm:h1"]["pid"] == os.getpid()
    subprocess.run([sys.executable, str(SCRIPT)], env=env, timeout=5,
                   input=json.dumps(hm("on_session_end", "h1")).encode())
    registry = json.loads((tmp_path / "cache" / "claudemetre" / "activity.json").read_text())
    assert registry == {}
