# host/ : côté WSL

`claudemetre_push.py` lit l'usage du forfait Claude sur l'endpoint d'usage
OAuth et le pousse au webhook de Home Assistant. `claudemetre_activity.py`
suit les agents au travail et ceux qui attendent une réponse, pour les
capteurs `binary_sensor.claude_actif` et `binary_sensor.claude_needattention`.
Les deux sont lancés par les hooks de Claude Code et de Hermes ; ils rendent
la main tout de suite et n'écrivent rien sur stdout. Conception :
[docs/logiciel.md](../docs/logiciel.md).

## Installation

Configuration (hors dépôt, mode 600) dans `~/.config/claudemetre/env` :

```sh
CLAUDEMETRE_HA_URL=<HA_URL de prive.env, à la racine du dépôt>
CLAUDEMETRE_WEBHOOK_ID=<même valeur que claudemetre_webhook_id dans secrets.yaml de HA>
CLAUDEMETRE_ACTIVITY_WEBHOOK_ID=<même valeur que claudemetre_activity_webhook_id>
```

Liens vers les scripts, utilisés par les hooks :

```sh
mkdir -p ~/.claude/hooks
ln -s ~/dev/claudemetre/host/claudemetre_push.py ~/.claude/hooks/claudemetre-push
ln -s ~/dev/claudemetre/host/claudemetre_activity.py ~/.claude/hooks/claudemetre-activity
```

Hooks Claude Code, dans `~/.claude/settings.json` (à côté des hooks existants) :

```json
"Stop":         [{"hooks": [{"type": "command", "command": "/home/<utilisateur>/.claude/hooks/claudemetre-push", "timeout": 5}]}],
"SessionStart": [{"hooks": [{"type": "command", "command": "/home/<utilisateur>/.claude/hooks/claudemetre-push", "timeout": 5}]}]
```

Hook Hermes, dans `~/.hermes/config.yaml`, avec le même chemin dans
`~/.hermes/shell-hooks-allowlist.json` (la passerelle ne demande jamais
l'accord elle-même) :

```yaml
hooks:
  post_llm_call:
    - command: "/home/<utilisateur>/.claude/hooks/claudemetre-push"
      timeout: 5
```

Hooks d'activité : la liste des événements est dans
[docs/logiciel.md](../docs/logiciel.md) (« Hooks d'activité »),
même forme (`command` + `timeout: 5`), côté Claude Code comme côté Hermes.
Chez Hermes, chaque profil a son propre `config.yaml` et son propre
`shell-hooks-allowlist.json` (`~/.hermes/profiles/<nom>/`) : un profil sans
hooks est invisible. `hermes [-p <profil>] hooks doctor` vérifie le tout.

## Utilisation

```sh
~/.claude/hooks/claudemetre-push --foreground   # un essai, journal sur stderr
~/.claude/hooks/claudemetre-activity --status   # agents suivis et compteurs
tail ~/.cache/claudemetre/log                   # ce qu'ont fait les hooks
uv run --no-project --with pytest pytest host/  # tests
```
