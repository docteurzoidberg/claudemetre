# D'où viennent les chiffres d'usage

Les chiffres viennent de l'**endpoint d'usage OAuth**, le même que `/usage` et que
Clawdmeter. Il n'est pas documenté.

```http
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken>
anthropic-beta: oauth-2025-04-20
Accept: application/json
```

Réponse :

```json
{"five_hour": {"utilization": 35.0, "resets_at": "2026-10-14T02:40:00Z"},
 "seven_day": {"utilization": 20.0, "resets_at": "2026-10-19T00:00:00Z"},
 "seven_day_opus": null,
 "extra_usage": {}, "limits": [...]}
```

- `utilization` : 0-100, en pourcentages entiers (`24.0`).
- `resets_at` : chaîne **ISO-8601**, avec microsecondes juste avant l'heure pile
  (`14:29:59.997686+00:00`), donc à arrondir à la seconde. `null` : session pas
  encore démarrée.
- Une vingtaine d'autres champs, presque tous nuls, et une liste `limits` qui répète
  les mêmes chiffres : on ne lit que `five_hour` et `seven_day`.
- Token : `~/.claude/.credentials.json`, `claudeAiOauth.accessToken` et `expiresAt`
  (ms).
- **Lecture seule** : ne jamais rafraîchir le token. S'il est expiré ou refusé
  (401/403), attendre que Claude Code le renouvelle.
- **429** : respecter `retry-after`. Claude Code mémorise un 429 par token pendant
  ~600 s, et sa commande `/usage` en souffrirait. Le script attend au moins 600 s,
  puis 1200 s et 1800 s après des échecs successifs, et ne descend jamais sous 120 s
  entre deux appels.
- L'appel n'envoie aucun message : il ne consomme aucun token et ne démarre pas de
  fenêtre de session.

L'endpoint reflète tout l'usage du compte, même hors Claude Code, mais il faut
l'appeler soi-même : ici, un script lancé par les hooks de Claude Code et de Hermes,
sans démon (voir [logiciel.md](logiciel.md)).

## Ce que les hooks et la statusline reçoivent

Les hooks reçoivent `session_id`, `cwd`, `hook_event_name`, etc., mais **aucun
chiffre d'usage** (<https://code.claude.com/docs/en/hooks>) : ils déclenchent la
lecture de l'endpoint, sans la remplacer.

La statusline reçoit bien l'usage, sur stdin, mais seulement pour le TUI
(<https://code.claude.com/docs/en/statusline>). C'est son schéma que le script
reprend pour envoyer les chiffres à HA :

```json
"rate_limits": {
  "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
  "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}
}
```

`used_percentage` : 0-100 ; `resets_at` : epoch Unix en **secondes**.

## Pourquoi l'ESP32 n'interroge pas l'endpoint lui-même

Il faudrait lui confier le token, qui expire et qu'il ne doit pas rafraîchir (le
refresh appartient à Claude Code). Le PC pousse donc des données déjà extraites, et
l'ESP32 ne détient aucun secret Anthropic. Même raisonnement pour Home Assistant : il
reçoit les chiffres, jamais le token.
