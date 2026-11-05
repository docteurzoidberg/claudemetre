[Version française](../logiciel.md)

# Software

How the software chain works, from Claude Code to the object. The principles are
in [specification.md](specification.md) (§ 3), the usage endpoint in
[data-source.md](data-source.md).

## Requirements

- The gauges reflect **all usage on the account**, not just the TUI:
  `claude -p` launched by other tools, Hermes, claude.ai.
- **No daemon**: a global hook in the WSL Claude Code profile
  (`~/.claude/settings.json`).

## No hook receives the numbers

| Mechanism | Receives usage | Runs for |
| --- | --- | --- |
| Claude Code hook | no | TUI, `claude -p` (except `--bare`) |
| Hermes hook | no | all Hermes sessions |
| OAuth usage endpoint | yes, the whole account | you have to call it yourself |

Hermes (`~/.hermes`, provider `anthropic`) doesn't call `claude`: it calls
the Anthropic API directly with the Claude Code OAuth login
(`credential_pool.anthropic`: `source: claude_code`). So no Claude Code mechanism
sees its calls.

## Hooks trigger, the endpoint provides the numbers

The hook doesn't carry the usage, it **triggers** reading it. A single script,
`claudemetre-push`, reads the OAuth usage endpoint (which sees the whole account) and pushes the
result to Home Assistant. It is launched by:

- a global Claude Code hook: `Stop` (end of each response) and `SessionStart`,
  in `~/.claude/settings.json`;
- a Hermes shell hook: `post_llm_call`, in `~/.hermes/config.yaml`.

```
Claude Code (TUI, claude -p) ── Stop / SessionStart hook ─┐
Hermes ─────────────────────── post_llm_call hook ────────┤
                                                          ▼
                     claudemetre-push (detached, max 1 call / 2 min)
                       ├─ reads ~/.claude/.credentials.json (read-only)
                       ├─ GET api.anthropic.com/api/oauth/usage
                       └─ POST ──► Home Assistant: webhook
                                     └─ template sensors (persistent)
                                          └─ native API ──► ESP32 ESPHome
```

**The endpoint uses no tokens**: it reads the account's counters, with no call to the
model. It doesn't count towards usage and doesn't open a session window. Its only
constraint is its own rate limit (429), hence the spacing between calls.

Coverage:

| Usage | Seen |
| --- | --- |
| Claude Code TUI | at the end of each response |
| `claude -p` (scripts, apps) | same, unless launched with `--bare` (hooks disabled) |
| Hermes | after each model response |
| claude.ai web / mobile | the next time Claude Code or Hermes triggers |

Home Assistant is the single entry point for the numbers; the object is only one of their
consumers. The script only does an HTTP POST, and the object stops updating when
HA is down.

### `claudemetre-push` script (`host/`)

- **Python 3 with the standard library only**, one file, run by the system
  `python3`. Versioned in `host/`, installed by symlink at
  `~/.claude/hooks/claudemetre-push`: the hooks don't depend on where the
  repository is.
- **Writes nothing to stdout**: in Claude Code, the output of a `Stop` hook can be
  read as a decision; in Hermes, a non-empty string returned by `post_llm_call`
  **replaces the response**. Errors go to a short log under `~/.cache/claudemetre/`.
- Returns within a few milliseconds: the work happens in a detached process
  (`setsid`), which the hook timeout can't kill.
- **Spacing** (shared state `~/.cache/claudemetre/state.json`, `flock` lock):
  - last call more than 120 s ago: call right away;
  - otherwise, a single catch-up call is scheduled for the end of the 120 s, so that the
    last response in a burst is counted;
  - 429: honor `retry-after`, at least 600 s, then 1200 s and 1800 s on successive
    failures.
- Token: reread on each call from `~/.claude/.credentials.json`
  (`claudeAiOauth.accessToken`, `expiresAt` in ms). **Never refreshed, never
  written**, never in a log. Expired, 401 or 403: no call, the next
  trigger will retry.
- 200 response: normalized to the statusline schema (`utilization` →
  `used_percentage`, ISO `resets_at` → epoch in seconds, **rounded to the nearest
  second**: truncated, `14:29:59.997` would give `14.29` on the display instead of
  `14.30`). `resets_at: null` = window not started, so 0 % with no reset time
  (known, unlike a missing window).
- Sent to HA on each successful measurement (at most one every 2 min). HA unreachable:
  nothing is kept, the next trigger measures again and resends.
- Configuration outside the repository: `~/.config/claudemetre/env` (mode 600) with the HA URL
  (`HA_URL` from `prive.env`, by IP: mDNS isn't guaranteed under WSL) and
  the webhook ID.
- `pytest` tests (`host/test_claudemetre_push.py`): normalization, `null` window,
  spacing and catch-up, expired token, 401, 429 and increasing wait, HA unreachable,
  empty stdout.

Body sent to HA (missing window = unknown, `resets_at: null` = not started):

```json
{"five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
 "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
 "measured_at": 1738420000, "source": "oauth"}
```

### Declaring the hooks

Installation: [host/README.md](../../host/README.md) (in French). Hermes asks you to accept a shell
hook the first time it runs (`hooks_auto_accept: false`).

### Transport: HA webhook and template sensors

File: [`homeassistant/packages/claudemetre.yaml`](../../homeassistant/packages/claudemetre.yaml),
installation described at the top of the file (in French). On the WSL side, the only secret is a
webhook ID, `local_only`, long and random (in HA's `secrets.yaml`). All the values
go out in one call, the state is restored when HA restarts, and the entities have a
`unique_id`.

- Each push carries the complete state read from the endpoint: the sensors keep nothing from one
  push to the next, and a null or missing window becomes "unknown".
- The `epoch` attribute of the reset sensors is for ESPHome, which reads it **as text**
  (`text_sensor: platform: homeassistant`): an ESPHome `sensor` is a 32-bit float, which
  only holds an epoch to within 128 s.
- When `resets_at` has passed with no new trigger, the device itself goes to
  0 % / `--.--` (specification § 3); HA corrects itself at the next measurement.

### Usage entities

| Entity | Type | Source |
| --- | --- | --- |
| `sensor.claude_usage_session` | % | `five_hour.used_percentage` |
| `sensor.claude_usage_semaine` | % | `seven_day.used_percentage` |
| `sensor.claude_reset_session` | timestamp (+ `epoch` attribute) | `five_hour.resets_at` |
| `sensor.claude_reset_semaine` | timestamp (+ `epoch` attribute) | `seven_day.resets_at` |
| `sensor.claude_derniere_mesure` | timestamp | `measured_at` |

The calibration and brightness `number` entities and the display mode `select` are
entities of the ESPHome device, not of this package.

## Claude activity

Two binary sensors in HA, for the CLAUDE indicator (see
[indicator.md](indicator.md)) and for other automations. They cover **all
running sessions**, in parallel, background subagents included, on the Claude Code side as well as
the Hermes side.

| Entity | On when | Attribute |
| --- | --- | --- |
| `binary_sensor.claude_actif` | at least one agent is working (turn in progress, not waiting) | `agents` |
| `binary_sensor.claude_needattention` | at least one agent is waiting for an answer | `demandes` |

"Waiting for an answer" = a dialog that blocks the agent: permission, multiple-choice
question (`AskUserQuestion`), plan approval (`ExitPlanMode`), MCP form; on the
Hermes side, `clarify`, command approval, sudo password. A question written as free
text at the end of a response is **not** counted: to the hooks, it is an end of turn
like any other, and nothing is guessed from the text.

### `claudemetre-activity` script (`host/claudemetre_activity.py`)

Same principle as `claudemetre-push`: standard library only, nothing on stdout,
control returned in 40 ms, the work in a detached process. Each hook updates a
shared registry (`~/.cache/claudemetre/activity.json`, under `flock`): one entry per
session and per subagent, with the agent's process (pid and start time), the time
the turn started and any current waits.

| Tool | Turn start | Turn end | Wait: start / end |
| --- | --- | --- | --- |
| Claude Code | `UserPromptSubmit`, `SubagentStart` | `Stop`, `StopFailure`, `SubagentStop`, `SessionEnd`, interrupted `PostToolUseFailure` | `PermissionRequest`, `PreToolUse` (questions), `Elicitation` / `PostToolUse(Failure)`, `PermissionDenied`, `ElicitationResult` |
| Hermes | `pre_llm_call`, `subagent_start` | `on_session_end` (each end of turn: succeeded, failed or interrupted), `subagent_stop` | `on_human_input_request` / `on_human_input_resolved` |

- A subagent has its own entry (`agent_id` in Claude Code, `child_session_id` in
  Hermes): the main session's `Stop` doesn't turn it off.
- A permission wait clears at the end of **that** tool (same name), not another one
  launched in parallel. Limitation: it stays on while the approved tool runs,
  because no hook reports the approval.
- `post_compaction` (Hermes): compaction can change the session ID, and the entry
  follows.
- `PostToolUse` hook on all tools (40 ms each); `PreToolUse` only on
  `AskUserQuestion|ExitPlanMode`.

Endings that are never reported are caught by a detached **watcher** that only lives while the
registry is not empty (every 3 s):

- agent process gone (kill, crash, terminal closed): entry removed;
- Escape or permission denied in Claude Code: no hook, but Claude Code writes
  `[Request interrupted by user…]` to the transcript; a marker later than the start of the
  turn ends it (only a `text` block that starts with the marker: a tool result
  that quotes it doesn't count);
- Escape before the first word of the response: Claude Code writes **nothing**, the transcript
  stops at the request (`api-request`). If nothing has followed for 10 min
  (`UNANSWERED_AFTER`), the turn is considered cancelled (main session only, not
  subagents); in practice, the message comes back to the input box and resending it puts
  the state right long before that;
- no event for 1 h (`STALE_AFTER`): entry dropped, except for a wait for an
  answer, which stays on as long as the process lives. Several minutes of thinking
  with no hook is not a problem: the watcher alone keeps the state alive in HA.

Sending to HA: a second webhook (`CLAUDEMETRE_ACTIVITY_WEBHOOK_ID`, secret
`claudemetre_activity_webhook_id`), when the counters change, then every 60 s as long
as one of them is non-zero. The sensors have a 3 min `auto_off`: with the PC off or WSL
stopped, they turn off by themselves.

```json
{"active": 2, "attention": 1, "updated_at": 1793183889, "source": "hooks"}
```

Not covered: claude.ai (web, mobile, app), `claude -p --bare`, Hermes profiles on
OpenRouter.

### Activity hooks

- Claude Code (`~/.claude/settings.json`): `UserPromptSubmit`, `PreToolUse` (matcher
  `AskUserQuestion|ExitPlanMode`), `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`,
  `PermissionDenied`, `Elicitation`, `ElicitationResult`, `SubagentStart`, `SubagentStop`,
  `Stop`, `StopFailure`, `SessionEnd` → `~/.claude/hooks/claudemetre-activity`.
- Hermes: `pre_llm_call`, `on_session_end`, `subagent_start`, `subagent_stop`,
  `post_compaction`, `on_human_input_request`, `on_human_input_resolved`, in
  `~/.hermes/config.yaml` and in the profiles on Anthropic, which also get the
  `post_llm_call` for usage. Approvals in each `shell-hooks-allowlist.json`; the
  gateway rereads the hooks in about 30 s, with no restart. `hermes hooks doctor`
  checks the lot.

`pytest` tests (`host/test_claudemetre_activity.py`): turns, parallel sessions, subagent
surviving `Stop`, waits, interruption, process gone, heartbeat, silent hook mode.

## Risks

- **Undocumented endpoint**: it may change. Fallback: the statusline, for the TUI only.
- **Login shared with Hermes**: `auth.adopt_external_logins: true` in
  `~/.hermes/config.yaml` makes it borrow **and refresh** the Claude Code login; refresh
  tokens are single-use, so the two programs can log each other out.
  The script only reads, but it suffers from these logouts. A login of Hermes's own
  would remove the conflict, and its usage would still count on the same account.
- **Nothing triggers** when neither Claude Code nor Hermes is running: usage on
  claude.ai during that time only shows up at the next trigger, and "last measurement"
  ages.

## ESPHome firmware

`esphome/claudemetre.yaml`, with the generic indicator package `esphome/temoin.yaml` (WS2812B
strip, `Fixe` / `Respiration` / `Clignotement` / `Balayage` effects (steady, breathing, blink,
sweep), brightness setting), which can be reused for the generator's indicators. The device
answers at `claudemetre.local`.

- `sensor: platform: homeassistant` for the two percentages, `text_sensor` for the two
  `epoch` attributes (converted to integers in the display lambda);
  `time: platform: homeassistant` for local time.
- States are read-only: no need to allow the device to call HA actions.
- TM1637 display lambda (`--.--` if unknown or passed); depending on the `select`
  `Afficheur mode`: `Heure de reset` (`HH.MM` in local time) or `Temps restant` (`-H.MM`,
  rounded up to the next minute), counted down by the ESP32 without the PC; the
  rest with native components.
- Display animations, in the same lambda: at startup, a lap at 12 frames
  per second during the 6 s test (`set_buffer`, one segment per bit); at session
  reset, 5 s of blinking at full brightness (200 ms `interval`). The reset is only
  watched for if it was seen coming: no blinking on restart for a reset that has already
  passed. One frame blocks the ESP32 for about 26 ms, hence this rate limited to the animation.
- Gauges calibrated at 5 points from HA: changing a point moves the gauge onto it for
  20 s, so you can set it by eye.

## `claudemetre-card` Lovelace card

A custom card for HA dashboards, which reproduces the look of the object (khaki
shell, black faceplate, two SO-45s with dark dials, SESSION / SEMAINE / RÉINIT. nameplates,
visor, yellow display, indicator) and reads the entities above.

Everything is SVG/CSS, with no background image: the scale comes from
`design/dials/dial_so45_spec.json` (same ticks as the printed dials); shell,
faceplate, flanges, nameplates, visor and display are drawn. **YAML configuration
only**, no visual editor.

- A single JS file, native web component (`customElements.define`, Shadow DOM), **no
  dependencies or build step**.
- 7-seg segments drawn in SVG from the exact outlines of the TM1637
  (`tm1637_segments.json`), unlit segments barely visible.
- Nameplate and dial text **as SVG paths**, same geometry as the printed dials
  and the Fusion nameplates (`so45_print.py`, `plaquettes_texte.py`): no
  `@font-face`, poorly supported in Shadow DOM. The paths are produced by
  `card_assets.py`, which rewrites the JS `ASSETS` block.
- Specific to the card (absent from the object): the display's **colon** (the object only has a
  dot), **red needles** and the **% value under the** SESSION and SEMAINE **nameplates**, dimmed along with the display when the data is stale.
  Colors adjustable through CSS variables (`--cm-needle`, `--cm-value`, `--cm-seg-on`,
  `--cm-kaki`…).
- Same rules as the device: needle gliding to the value (slow CSS transition);
  separator blinking when a time is shown; reset passed → 0 % and `--:--` without
  waiting for HA (30 s timer), for the session as well as the week (hence `week_reset`);
  unknown sensor → needle at rest and `--:--`. Stale data (`dernière mesure` too
  old or unknown) → display dimmed.
- `HH:MM` time in HA's time zone (`hass.config.time_zone`), via `Intl.DateTimeFormat`.
- Click on a gauge, the display or the indicator → the entity's "more info" dialog (indicator:
  `attention` when it is red, `active` otherwise).
- **Indicator**: khaki frame with its visor, CLAUDE legend in a black mask, on the row of
  SESSION / SEMAINE nameplates. It still has to be realigned with the object's indicator (card: frame
  40 × 18, window 27 × 10.5, with visor; object: frame 52 × 18, window 32 × 11, capitals
  of 6.64 mm, no visor). States, as on the object: blinking red (1 s) when
  `attention` is `on`, takes priority; breathing amber (1.6 s) when `active` is `on`; off
  otherwise, including unknown, unavailable or missing. No dimming when the usage data
  is stale: these sensors have their own 3 min `auto_off`. Tooltip: "Claude au
  travail (2 agents)" (working), "Claude attend une réponse" (waiting for an answer), "Claude au
  repos" (idle) or "Activité de Claude inconnue" (unknown). Colors: `--cm-lamp-amber`,
  `--cm-lamp-red`, `--cm-lamp-off`. No animation if the system asks for reduced motion.
- Configuration, with these default values:

```yaml
type: custom:claudemetre-card
entities:
  session: sensor.claude_usage_session
  week: sensor.claude_usage_semaine
  session_reset: sensor.claude_reset_session
  week_reset: sensor.claude_reset_semaine
  last_measure: sensor.claude_derniere_mesure   # null: never dimmed
  active: binary_sensor.claude_actif            # amber indicator
  attention: binary_sensor.claude_needattention # red indicator, takes priority
stale_after: 30   # minutes
```

### Card files

| File | Role |
| --- | --- |
| `homeassistant/www/claudemetre/claudemetre-card.js` | the card, the only file to copy to HA |
| `homeassistant/card-dev/card_assets.py` | rewrites the JS `ASSETS` block (`uv run card_assets.py`) after a change to the dials, nameplates, indicator legend or display |
| `homeassistant/card-dev/preview.html` | preview without HA: fake `hass` driven by sliders (value, `unknown`, `unavailable`, missing entity; number of agents and requests for the two binary sensors), HA time zone, scenarios, six cards (light / dark × 320 px, 492 px, full width), log of errors and "more info" events |

Preview, from the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory homeassistant
```

then `http://localhost:8765/card-dev/preview.html` (also from Windows, since WSL is in mirrored
networking mode). URL parameters: `?scenario=Périmé` (or another scenario name); `?verifier`
runs the automatic check, also available through the `Vérifier` button: each
scenario, two time zones, the reset passing with no new push from HA (31 s wait), the "more
info" clicks and rejected configurations, comparing the state read from each card
(needles, values, lit segments, dimming, indicator state, animation and tooltip) with
a calculation done independently by the page. With no browser on screen:

```sh
chromium-browser --headless=new --virtual-time-budget=45000 --dump-dom \
  "http://127.0.0.1:8765/card-dev/preview.html?verifier" | grep -o "<title>[^<]*"
```

(`<title>OK` or `<title>ÉCHEC n`, details in the page log).

### Deploying the card

In HA: the file goes in `<config>/www/claudemetre/claudemetre-card.js`, declared as a
`/local/claudemetre/claudemetre-card.js` resource of type module (Settings > Dashboards >
Resources, in advanced mode). Add `?v=N` to the resource URL on each update to
get around the browser cache.

HA's config is reachable through the Samba share (`HA_SAMBA` and `HA_SAMBA_USER` from
`prive.env`), already open in the Windows session: from WSL, go through `cmd.exe` (the
folder is also a git repository). Copying the card:

```sh
. ./prive.env
cp homeassistant/www/claudemetre/claudemetre-card.js "$WIN_TEMP/claudemetre/"
cd /mnt/c && cmd.exe /c "copy /Y %TEMP%\claudemetre\claudemetre-card.js $HA_SAMBA\www\claudemetre\"
```

Dashboards are in *storage* mode: resources and cards are declared in the UI,
not by editing `.storage/` (HA rewrites it from memory).
