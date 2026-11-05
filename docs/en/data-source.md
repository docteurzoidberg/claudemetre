[Version française](../source-donnees.md)

# Where the usage numbers come from

The numbers come from the **OAuth usage endpoint**, the same one as `/usage` and
Clawdmeter. It is undocumented.

```http
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken>
anthropic-beta: oauth-2025-04-20
Accept: application/json
```

Response:

```json
{"five_hour": {"utilization": 35.0, "resets_at": "2026-10-14T02:40:00Z"},
 "seven_day": {"utilization": 20.0, "resets_at": "2026-10-19T00:00:00Z"},
 "seven_day_opus": null,
 "extra_usage": {}, "limits": [...]}
```

- `utilization`: 0-100, in whole percentages (`24.0`).
- `resets_at`: **ISO-8601** string, with microseconds just before the top of the hour
  (`14:29:59.997686+00:00`), so it has to be rounded to the second. `null`: session not
  started yet.
- About twenty other fields, almost all null, and a `limits` list that repeats
  the same numbers: only `five_hour` and `seven_day` are read.
- Token: `~/.claude/.credentials.json`, `claudeAiOauth.accessToken` and `expiresAt`
  (ms).
- **Read-only**: never refresh the token. If it is expired or rejected
  (401/403), wait for Claude Code to renew it.
- **429**: honor `retry-after`. Claude Code remembers a 429 per token for
  ~600 s, and its `/usage` command would suffer. The script waits at least 600 s,
  then 1200 s and 1800 s after successive failures, and never goes below 120 s
  between two calls.
- The call sends no message: it uses no tokens and doesn't start a
  session window.

The endpoint reflects all usage on the account, even outside Claude Code, but you have
to call it yourself: here, a script launched by the Claude Code and Hermes hooks,
with no daemon (see [software.md](software.md)).

## What the hooks and the statusline receive

Hooks receive `session_id`, `cwd`, `hook_event_name`, etc., but **no
usage numbers** (<https://code.claude.com/docs/en/hooks>): they trigger the
endpoint read, without replacing it.

The statusline does receive usage, on stdin, but only for the TUI
(<https://code.claude.com/docs/en/statusline>). The script reuses its schema
to send the numbers to HA:

```json
"rate_limits": {
  "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
  "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}
}
```

`used_percentage`: 0-100; `resets_at`: Unix epoch in **seconds**.

## Why the ESP32 doesn't query the endpoint itself

It would have to be given the token, which expires and which it must not refresh (the
refresh belongs to Claude Code). So the PC pushes data that has already been extracted, and
the ESP32 holds no Anthropic secret. The same reasoning applies to Home Assistant: it
receives the numbers, never the token.
