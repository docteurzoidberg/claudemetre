#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Pousse l'usage du forfait Claude vers Home Assistant.

Lancé par les hooks de Claude Code (Stop, SessionStart) et de Hermes
(post_llm_call). Le hook ne transporte pas les chiffres : il déclenche la
lecture de l'endpoint d'usage OAuth, qui voit tout l'usage du compte (TUI,
claude -p, Hermes, claude.ai), puis l'envoi au webhook de Home Assistant.
Détail : docs/logiciel.md.

Usage :
  claudemetre-push               mode hook : rend la main tout de suite sans rien
                                 écrire sur stdout ; le travail continue dans un
                                 processus détaché
  claudemetre-push --foreground  même travail au premier plan, journal sur stderr

Au plus un appel à l'endpoint toutes les 2 min ; un déclenchement trop proche
programme un seul appel de rattrapage, pour que la dernière réponse d'une
rafale soit comptée. Le jeton OAuth de Claude Code est lu, jamais rafraîchi ni
réécrit, jamais journalisé. L'endpoint ne consomme aucun token.

Configuration : ~/.config/claudemetre/env (CLAUDEMETRE_HA_URL,
CLAUDEMETRE_WEBHOOK_ID). État et journal : ~/.cache/claudemetre/.
"""
import fcntl
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
MIN_INTERVAL = 120                  # s entre deux appels à l'endpoint
BACKOFF_STEPS = (600, 1200, 1800)   # s d'attente après des 429 successifs
TOKEN_MARGIN = 60                   # s : jeton tenu pour expiré un peu avant l'heure
LOG_MAX_BYTES = 100_000
WINDOWS = ("five_hour", "seven_day")

HOME = Path.home()
CONFIG_FILE = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "claudemetre" / "env"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "claudemetre"
CREDENTIALS_FILE = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude")) / ".credentials.json"

_echo = False  # --foreground : journal recopié sur stderr


def log(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n"
    if _echo:
        sys.stderr.write(line)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / "log"
        if path.exists() and path.stat().st_size > LOG_MAX_BYTES:
            path.replace(path.with_suffix(".1"))
        with path.open("a") as f:
            f.write(line)
    except OSError:
        pass


@contextmanager
def locked_state():
    """État partagé entre les déclenchements, sous verrou exclusif."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with (CACHE_DIR / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = CACHE_DIR / "state.json"
        try:
            state = json.loads(path.read_text())
        except (OSError, ValueError):
            state = {}
        yield state
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        tmp.replace(path)


def schedule(state, now):
    """Décide quoi faire d'un déclenchement : "fetch", "wait" ou "skip"."""
    if now < state.get("backoff_until", 0):
        return "skip"
    if now - state.get("last_fetch", 0) >= MIN_INTERVAL:
        state["last_fetch"] = now
        return "fetch"
    if state.get("pending_until", 0) > now:
        return "skip"  # un appel de rattrapage est déjà programmé
    state["pending_until"] = state["last_fetch"] + MIN_INTERVAL
    return "wait"


def resume(state, now):
    """Fin d'attente de l'appel de rattrapage."""
    state.pop("pending_until", None)
    if now < state.get("backoff_until", 0):
        return "skip"
    state["last_fetch"] = now
    return "fetch"


def record_result(state, status, retry_after, now):
    """Met à jour l'attente après un appel à l'endpoint."""
    if status == 429:
        step = state.get("backoff_step", 0)
        wait = max(retry_after or 0, BACKOFF_STEPS[min(step, len(BACKOFF_STEPS) - 1)])
        state["backoff_until"] = now + wait
        state["backoff_step"] = step + 1
    elif status == 200:
        state.pop("backoff_until", None)
        state.pop("backoff_step", None)


def read_config(required=("CLAUDEMETRE_HA_URL", "CLAUDEMETRE_WEBHOOK_ID")):
    config = {}
    try:
        for line in CONFIG_FILE.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.lstrip().startswith("#"):
                config[key.strip()] = value.strip().strip("\"'")
    except OSError:
        pass
    if not all(config.get(key) for key in required):
        return None
    return config


def read_token(now):
    """Jeton d'accès de Claude Code, ou None s'il manque ou a expiré. Lecture seule."""
    try:
        oauth = json.loads(CREDENTIALS_FILE.read_text())["claudeAiOauth"]
        token, expires_ms = oauth["accessToken"], oauth["expiresAt"]
    except (OSError, ValueError, KeyError, TypeError):
        log(f"jeton absent ou illisible : {CREDENTIALS_FILE}")
        return None
    if expires_ms / 1000 < now + TOKEN_MARGIN:
        log("jeton expiré : on attend que Claude Code ou Hermes le renouvelle")
        return None
    return token


def parse_retry_after(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fetch_usage(token):
    """GET de l'endpoint d'usage : (statut, corps JSON, retry-after en s)."""
    import urllib.error, urllib.request  # à la demande : voir push()
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r), None
    except urllib.error.HTTPError as e:
        return e.code, None, parse_retry_after(e.headers.get("retry-after"))
    except (OSError, ValueError) as e:
        log(f"endpoint d'usage injoignable : {e}")
        return None, None, None


def to_epoch(iso):
    """Date ISO → epoch arrondi à la seconde (14:29:59.997 → 14:30:00)."""
    if not isinstance(iso, str):
        return None
    try:
        return round(datetime.fromisoformat(iso).timestamp())
    except ValueError:
        return None


def normalize(usage, now):
    """Réponse de l'endpoint → corps du webhook, au schéma de la statusline."""
    body = {}
    for key in WINDOWS:
        window = usage.get(key)
        pct = window.get("utilization") if isinstance(window, dict) else None
        if not isinstance(pct, (int, float)):
            body[key] = None  # inconnue
            continue
        body[key] = {
            "used_percentage": int(pct) if float(pct).is_integer() else round(pct, 1),
            "resets_at": to_epoch(window.get("resets_at")),  # None : pas commencée
        }
    body["measured_at"] = int(now)
    body["source"] = "oauth"
    return body


def push(config, body, webhook_key="CLAUDEMETRE_WEBHOOK_ID"):
    """POST au webhook de Home Assistant : statut HTTP, ou None si injoignable."""
    # urllib importé à la demande : claudemetre-activity importe ce module à
    # chaque appel d'outil, et urllib.request coûte 40 ms au démarrage
    import urllib.error, urllib.request
    url = f"{config['CLAUDEMETRE_HA_URL'].rstrip('/')}/api/webhook/{config[webhook_key]}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError as e:
        log(f"Home Assistant injoignable : {e}")
        return None


def describe(window):
    return "?" if window is None else f"{window['used_percentage']} %"


def run():
    """Un déclenchement : espacement, lecture de l'endpoint, envoi à HA."""
    config = read_config()
    if config is None:
        log(f"configuration incomplète : {CONFIG_FILE}")
        return
    with locked_state() as state:
        action = schedule(state, time.time())
        pending_until = state.get("pending_until", 0)
    if action == "wait":
        time.sleep(max(0.0, pending_until - time.time()))
        with locked_state() as state:
            action = resume(state, time.time())
    if action == "skip":
        return

    now = time.time()
    token = read_token(now)
    if token is None:
        return
    status, usage, retry_after = fetch_usage(token)
    with locked_state() as state:
        record_result(state, status, retry_after, now)
        backoff_until = state.get("backoff_until", 0)
    if status == 429:
        log(f"endpoint : HTTP 429, prochain appel dans {round(backoff_until - now)} s")
        return
    if status != 200 or not isinstance(usage, dict):
        if status is not None:
            log(f"endpoint : HTTP {status}")
        return

    body = normalize(usage, now)
    ha_status = push(config, body)
    log(f"session {describe(body['five_hour'])}, semaine {describe(body['seven_day'])}"
        f" → Home Assistant : {ha_status or 'échec'}")


def drain_stdin():
    """Lit et jette la charge utile du hook, pour que l'appelant ne bute pas sur un tube fermé."""
    if sys.stdin is not None and not sys.stdin.isatty():
        try:
            sys.stdin.buffer.read()
        except OSError:
            pass


def detach():
    """Rend la main au hook ; le travail continue dans un processus détaché."""
    if os.fork() > 0:
        os._exit(0)
    os.setsid()  # hors du groupe de processus du hook : son délai ne le coupe pas
    if os.fork() > 0:
        os._exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):  # stdout fermé : l'appelant n'attend pas la fin
        os.dup2(devnull, fd)


def main(argv):
    global _echo
    if "--foreground" in argv:
        _echo = True
    else:
        drain_stdin()
        detach()
    try:
        run()
    except Exception as e:  # un hook ne doit jamais gêner Claude Code ni Hermes
        log(f"erreur : {e!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
