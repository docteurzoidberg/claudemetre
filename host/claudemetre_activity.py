#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Pousse l'activité de Claude vers Home Assistant : agents au travail, agents
qui attendent une réponse.

Lancé par les hooks de Claude Code et de Hermes. Chaque hook met à jour un
registre partagé : une entrée par session et par sous-agent, avec le
processus de l'agent et ses attentes en cours (permission, question). Deux
compteurs en sortent :

  active     agents au travail (un tour en cours, sans attente)
  attention  agents qui attendent une réponse de l'utilisateur

Un processus détaché envoie les compteurs au webhook de HA quand ils changent,
puis surveille le registre tant qu'il n'est pas vide (pas de démon permanent).
Il retire une entrée dont la fin n'a pas été signalée : processus de l'agent
disparu, interruption (Échap) notée par Claude Code dans le transcript,
requête au modèle restée 10 min sans aucune réponse (Échap avant le premier
mot, qui ne laisse aucune trace), ou une heure sans événement (sauf attente de
réponse). Il renvoie l'état toutes les
60 s ; sans nouvelles, HA éteint seul les capteurs (auto_off). Détail :
docs/logiciel.md.

Usage :
  claudemetre-activity            mode hook : charge utile JSON sur stdin, rend
                                  la main tout de suite sans rien écrire sur stdout
  claudemetre-activity --status   registre et compteurs

Configuration : ~/.config/claudemetre/env (CLAUDEMETRE_HA_URL,
CLAUDEMETRE_ACTIVITY_WEBHOOK_ID). Registre et journal : ~/.cache/claudemetre/.
"""
import fcntl
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime

import claudemetre_push as cp

POLL = 3              # s entre deux passages du surveillant
HEARTBEAT = 60        # s : état renvoyé à HA tant qu'un compteur est non nul
STALE_AFTER = 3600    # s sans événement : entrée sans attente abandonnée
UNANSWERED_AFTER = 600  # s : requête au modèle sans aucune réponse écrite, tour tenu pour annulé
TAIL_BYTES = 65536    # fin du transcript lue pour y chercher une interruption
INTERRUPT_MARK = "[Request interrupted by user"
CONVERSATION = {"user", "assistant", "system", "api-request"}  # enregistrements datés du transcript
SHELLS = {"sh", "dash", "bash", "zsh", "fish", "env", "timeout"}
ASKING_TOOLS = {"AskUserQuestion", "ExitPlanMode"}  # outils de Claude Code qui questionnent
WEBHOOK_KEY = "CLAUDEMETRE_ACTIVITY_WEBHOOK_ID"


@contextmanager
def locked(name):
    cp.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with (cp.CACHE_DIR / name).open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


@contextmanager
def locked_registry():
    """Registre des agents, partagé entre les hooks, sous verrou exclusif."""
    with locked("activity.lock"):
        path = cp.CACHE_DIR / "activity.json"
        try:
            entries = json.loads(path.read_text())
        except (OSError, ValueError):
            entries = {}
        yield entries
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries))
        tmp.replace(path)


# --- processus de l'agent ----------------------------------------------------

def proc_stat(pid):
    """(nom, ppid, date de démarrage) d'un processus, ou None s'il n'existe plus."""
    try:
        raw = open(f"/proc/{pid}/stat").read()
    except (OSError, TypeError):
        return None
    fields = raw[raw.rindex(")") + 2:].split()
    return raw[raw.index("(") + 1:raw.rindex(")")], int(fields[1]), int(fields[19])


def agent_process():
    """(pid, date de démarrage) de l'agent qui lance le hook : premier ancêtre
    qui n'est pas un shell. La date déjoue la réutilisation du pid."""
    pid = os.getppid()
    stat = proc_stat(pid)
    while stat and stat[0] in SHELLS and stat[1] > 1:
        pid = stat[1]
        stat = proc_stat(pid)
    return pid, stat[2] if stat else None


def alive(entry):
    if entry.get("pid") is None:
        return True  # inconnu : on laisse faire les autres garde-fous
    stat = proc_stat(entry["pid"])
    return stat is not None and stat[2] == entry.get("start")


# --- événements des hooks ----------------------------------------------------

def touch(entries, key, now, process, transcript=None, new_turn=False, turn=True):
    """Entrée de l'agent, créée au besoin ; new_turn repart d'un tour neuf."""
    entry = entries.get(key)
    if entry is None or new_turn:
        entry = entries[key] = {"since": now, "turn": turn, "waits": {}}
    entry["turn"] = entry["turn"] or turn
    entry["seen"] = now
    entry["pid"], entry["start"] = process
    if transcript:
        entry["transcript"] = transcript
    return entry


def claude_code_event(entries, event, p, now, process):
    main = f"cc:{p.get('session_id')}"
    key = f"{main}:{p['agent_id']}" if p.get("agent_id") else main  # sous-agent
    transcript = p.get("transcript_path")
    tool_wait = f"tool:{p.get('tool_name')}"
    elicit_wait = f"elicit:{p.get('elicitation_id') or p.get('mcp_server_name')}"

    if event in ("UserPromptSubmit", "SubagentStart"):
        touch(entries, key, now, process, transcript, new_turn=True)
    elif event in ("Stop", "StopFailure", "SubagentStop"):
        entries.pop(key, None)
    elif event == "SessionEnd":
        for k in [k for k in entries if k == main or k.startswith(main + ":")]:
            del entries[k]
    elif event == "PostToolUseFailure" and p.get("is_interrupt"):
        entries.pop(key, None)
    elif event == "PermissionRequest" or (event == "PreToolUse" and p.get("tool_name") in ASKING_TOOLS):
        touch(entries, key, now, process, transcript)["waits"][tool_wait] = now
    elif event in ("PostToolUse", "PostToolUseFailure", "PermissionDenied"):
        # par nom d'outil : un outil lancé en parallèle ne lève pas l'attente d'un autre
        touch(entries, key, now, process, transcript)["waits"].pop(tool_wait, None)
    elif event == "Elicitation":
        touch(entries, key, now, process, transcript)["waits"][elicit_wait] = now
    elif event in ("ElicitationResult", "PreToolUse"):
        touch(entries, key, now, process, transcript)["waits"].pop(elicit_wait, None)


def hermes_event(entries, event, p, now, process):
    extra = p.get("extra") or {}
    key = f"hm:{p.get('session_id') or ''}"
    child = f"hm:{extra.get('child_session_id')}"
    ask_wait = f"ask:{extra.get('request_id')}"

    if event == "pre_llm_call":
        touch(entries, key, now, process, new_turn=True)
    elif event in ("post_llm_call", "on_session_end"):  # on_session_end : chaque fin de tour
        entries.pop(key, None)
    elif event == "subagent_start":
        touch(entries, child, now, process, new_turn=True)
    elif event == "subagent_stop":
        entries.pop(child, None)
    elif event == "post_compaction":  # la compaction peut changer l'identifiant de session
        entry = entries.pop(f"hm:{extra.get('old_session_id')}", None)
        if entry is not None:
            entries[key] = entry
    elif event == "on_human_input_request":  # approbation, sudo, question (clarify)
        touch(entries, key, now, process, turn=False)["waits"][ask_wait] = now
    elif event == "on_human_input_resolved":
        for entry in entries.values():
            entry["waits"].pop(ask_wait, None)


def apply_event(entries, payload, now, process):
    event = payload.get("hook_event_name") or ""
    if "extra" in payload:  # charge utile des hooks shell de Hermes
        hermes_event(entries, event, payload, now, process)
    else:
        claude_code_event(entries, event, payload, now, process)
    for key in [k for k, e in entries.items() if not e["turn"] and not e["waits"]]:
        del entries[key]


def counts(entries):
    """(agents au travail, agents qui attendent une réponse)."""
    active = sum(1 for e in entries.values() if e["turn"] and not e["waits"])
    attention = sum(1 for e in entries.values() if e["waits"])
    return active, attention


# --- fins non signalées ------------------------------------------------------

def to_epoch(iso):
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return None


def read_transcript_tail(path):
    """(dernière interruption, requête au modèle restée sans réponse) d'après
    la fin du transcript : heures epoch, 0 s'il n'y en a pas.

    Claude Code n'émet aucun hook quand on interrompt une réponse (Échap) ou
    qu'on refuse une permission ; il écrit « [Request interrupted by user…] »
    dans le transcript. Échap avant le premier mot de la réponse n'écrit même
    pas cela : le transcript s'arrête sur la requête (api-request)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            tail = f.read().decode(errors="replace")
    except (OSError, TypeError):
        return 0, 0
    unanswered = None
    for line in reversed(tail.splitlines()):
        try:
            record = json.loads(line)
        except ValueError:
            continue  # ligne coupée en début de lecture ou en cours d'écriture
        kind = record.get("type")
        if kind not in CONVERSATION:
            continue
        if unanswered is None:
            unanswered = (to_epoch(record.get("timestamp")) or 0) if kind == "api-request" else 0
        if kind == "user" and INTERRUPT_MARK in line and is_interrupt(record):
            return to_epoch(record.get("timestamp")) or 0, unanswered
    return 0, unanswered or 0


def is_interrupt(record):
    """Message de Claude Code dont un bloc texte commence par la marque ; un
    résultat d'outil (bloc tool_result) qui la cite ne compte pas."""
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content.startswith(INTERRUPT_MARK)
    return any(isinstance(b, dict) and b.get("type") == "text"
               and str(b.get("text", "")).startswith(INTERRUPT_MARK) for b in content or [])


def prune(entries, now):
    """Retire les entrées dont la fin n'a pas été signalée : [(clé, raison)]."""
    tails = {}
    removed = []
    for key, entry in list(entries.items()):
        transcript = entry.get("transcript")
        if transcript and transcript not in tails:
            tails[transcript] = read_transcript_tail(transcript)
        interrupted, unanswered = tails.get(transcript, (0, 0))
        main_turn = key.startswith("cc:") and key.count(":") == 1  # pas un sous-agent
        if not alive(entry):
            reason = "processus disparu"
        elif interrupted > entry["since"]:
            reason = "interruption"
        elif (main_turn and not entry["waits"]
              and entry["since"] < unanswered < now - UNANSWERED_AFTER):
            reason = "sans réponse du modèle"
        elif not entry["waits"] and now - entry["seen"] > STALE_AFTER:
            reason = "sans nouvelles"
        else:
            continue
        del entries[key]
        removed.append((key, reason))
    return removed


# --- envoi à Home Assistant --------------------------------------------------

def publish(now):
    """Envoie les compteurs à HA s'ils ont changé ; sinon les renvoie toutes les
    HEARTBEAT s tant que l'un d'eux est non nul ou que l'envoi précédent a échoué."""
    with locked("push.lock"):  # un envoi à la fois, avec l'état le plus récent
        with locked_registry() as entries:
            active, attention = counts(entries)
        sent_path = cp.CACHE_DIR / "activity-sent.json"
        try:
            sent = json.loads(sent_path.read_text())
        except (OSError, ValueError):
            sent = {}
        changed = [active, attention] != [sent.get("active"), sent.get("attention")]
        due = (active or attention or not sent.get("ok")) and now - sent.get("at", 0) >= HEARTBEAT
        if not (changed or due):
            return
        config = cp.read_config(("CLAUDEMETRE_HA_URL", WEBHOOK_KEY))
        if config is None:
            status = None
            cp.log(f"configuration incomplète pour l'activité : {cp.CONFIG_FILE}")
        else:
            status = cp.push(config, {"active": active, "attention": attention,
                                      "updated_at": int(now), "source": "hooks"}, WEBHOOK_KEY)
        sent_path.write_text(json.dumps({"active": active, "attention": attention,
                                         "at": now, "ok": status == 200}))
    if changed:
        cp.log(f"activité : {active} au travail, {attention} en attente"
               f" → Home Assistant : {status or 'échec'}")


def watch():
    """Surveille le registre tant qu'il n'est pas vide ; un seul surveillant à la fois."""
    lock = (cp.CACHE_DIR / "watch.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return  # un autre surveillant tourne déjà
    while True:
        time.sleep(POLL)
        now = time.time()
        with locked_registry() as entries:
            removed = prune(entries, now)
            empty = not entries
            if empty:
                # rendu sous le verrou du registre : le hook qui ajoute la
                # prochaine entrée trouvera le verrou libre et prendra le relais
                lock.close()
        for key, reason in removed:
            cp.log(f"activité : {key} retiré ({reason})")
        publish(now)
        if empty:
            return


def status():
    with locked_registry() as entries:
        active, attention = counts(entries)
        for key, e in entries.items():
            state = "attend " + ", ".join(e["waits"]) if e["waits"] else "au travail"
            print(f"{key}  {state}  depuis {time.strftime('%H:%M:%S', time.localtime(e['since']))}"
                  f"  pid {e.get('pid')}")
    print(f"{active} au travail, {attention} en attente")


def main(argv):
    if "--status" in argv:
        status()
        return
    try:
        payload = json.loads(sys.stdin.buffer.read() or b"{}")
        with locked_registry() as entries:
            apply_event(entries, payload, time.time(), agent_process())
    except Exception as e:  # un hook ne doit jamais gêner Claude Code ni Hermes
        cp.log(f"activité, erreur : {e!r}")
    cp.detach()
    try:
        publish(time.time())
        watch()
    except Exception as e:
        cp.log(f"activité, erreur : {e!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
