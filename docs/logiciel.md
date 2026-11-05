# Partie logicielle

Fonctionnement de la chaîne logicielle, de Claude Code à l'objet. Les principes sont
dans [cahier-des-charges.md](cahier-des-charges.md) (§ 3), l'endpoint d'usage dans
[source-donnees.md](source-donnees.md).

## Exigences

- Les jauges reflètent **tout l'usage du compte**, pas seulement le TUI :
  `claude -p` lancé par d'autres outils, Hermes, claude.ai.
- **Pas de démon** : un hook global dans le profil Claude Code de WSL
  (`~/.claude/settings.json`).

## Aucun hook ne reçoit les chiffres

| Mécanisme | Reçoit l'usage | Tourne pour |
| --- | --- | --- |
| Hook Claude Code | non | TUI, `claude -p` (sauf `--bare`) |
| Hook Hermes | non | toutes les sessions Hermes |
| Endpoint d'usage OAuth | oui, tout le compte | à appeler soi-même |

Hermes (`~/.hermes`, provider `anthropic`) n'appelle pas `claude` : il appelle
directement l'API Anthropic avec le login OAuth de Claude Code
(`credential_pool.anthropic` : `source: claude_code`). Aucun mécanisme de Claude Code
ne voit donc ses appels.

## Les hooks déclenchent, l'endpoint fournit les chiffres

Le hook ne transporte pas l'usage, il **déclenche** sa lecture. Un seul script,
`claudemetre-push`, lit l'endpoint d'usage OAuth (qui voit tout le compte) et pousse le
résultat vers Home Assistant. Il est lancé par :

- un hook global de Claude Code : `Stop` (fin de chaque réponse) et `SessionStart`,
  dans `~/.claude/settings.json` ;
- un hook shell de Hermes : `post_llm_call`, dans `~/.hermes/config.yaml`.

```
Claude Code (TUI, claude -p) ── hook Stop / SessionStart ─┐
Hermes ─────────────────────── hook post_llm_call ────────┤
                                                          ▼
                     claudemetre-push (détaché, 1 appel / 2 min max)
                       ├─ lit ~/.claude/.credentials.json (lecture seule)
                       ├─ GET api.anthropic.com/api/oauth/usage
                       └─ POST ──► Home Assistant : webhook
                                     └─ capteurs template (persistants)
                                          └─ API native ──► ESP32 ESPHome
```

**L'endpoint ne consomme aucun token** : il lit les compteurs du compte, sans appel au
modèle. Il ne compte pas dans l'usage et n'ouvre pas de fenêtre de session. Sa seule
contrainte est sa propre limite de débit (429), d'où l'espacement des appels.

Couverture :

| Usage | Vu |
| --- | --- |
| TUI Claude Code | à la fin de chaque réponse |
| `claude -p` (scripts, applis) | idem, sauf lancé en `--bare` (hooks désactivés) |
| Hermes | après chaque réponse du modèle |
| claude.ai web / mobile | au prochain déclenchement par Claude Code ou Hermes |

Home Assistant est le point d'entrée unique des chiffres, l'objet n'est qu'un de leurs
consommateurs. Le script ne fait qu'un POST HTTP, et l'objet ne se met plus à jour quand
HA est arrêté.

### Script `claudemetre-push` (`host/`)

- **Python 3 de la bibliothèque standard seule**, un fichier, lancé par le `python3`
  système. Versionné dans `host/`, installé par lien symbolique dans
  `~/.claude/hooks/claudemetre-push` : les hooks ne dépendent pas de l'emplacement du
  dépôt.
- **N'écrit rien sur stdout** : chez Claude Code, la sortie d'un hook `Stop` peut être
  lue comme une décision ; chez Hermes, une chaîne non vide renvoyée par `post_llm_call`
  **remplace la réponse**. Erreurs dans un journal court sous `~/.cache/claudemetre/`.
- Rend la main en quelques millisecondes : le travail se fait dans un processus détaché
  (`setsid`), que le délai du hook ne peut pas couper.
- **Espacement** (état partagé `~/.cache/claudemetre/state.json`, verrou `flock`) :
  - dernier appel il y a plus de 120 s : appel tout de suite ;
  - sinon, un seul appel de rattrapage est programmé pour la fin des 120 s, pour que la
    dernière réponse d'une rafale soit comptée ;
  - 429 : respecter `retry-after`, au moins 600 s, puis 1200 s et 1800 s en cas d'échecs
    successifs.
- Jeton : relu à chaque appel dans `~/.claude/.credentials.json`
  (`claudeAiOauth.accessToken`, `expiresAt` en ms). **Jamais de rafraîchissement, jamais
  d'écriture**, jamais dans un journal. Expiré, 401 ou 403 : pas d'appel, le prochain
  déclenchement réessaiera.
- Réponse 200 : normalisation au schéma de la statusline (`utilization` →
  `used_percentage`, `resets_at` ISO → epoch en secondes, **arrondi à la seconde la plus
  proche** : tronqué, `14:29:59.997` donnerait `14.29` sur l'afficheur au lieu de
  `14.30`). `resets_at: null` = fenêtre pas commencée, donc 0 % sans heure de reset
  (connu, à la différence d'une fenêtre absente).
- Envoi à HA à chaque mesure réussie (au plus une toutes les 2 min). HA injoignable :
  rien n'est gardé, le déclenchement suivant remesure et renvoie.
- Configuration hors dépôt : `~/.config/claudemetre/env` (mode 600) avec l'URL de HA
  (`HA_URL` de `prive.env`, par IP : le mDNS n'est pas garanti sous WSL) et
  l'identifiant du webhook.
- Tests `pytest` (`host/test_claudemetre_push.py`) : normalisation, fenêtre `null`,
  espacement et rattrapage, jeton expiré, 401, 429 et attente croissante, HA injoignable,
  stdout vide.

Corps envoyé à HA (fenêtre absente = inconnue, `resets_at: null` = pas commencée) :

```json
{"five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
 "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
 "measured_at": 1738420000, "source": "oauth"}
```

### Déclaration des hooks

Installation : [host/README.md](../host/README.md). Hermes demande d'accepter un hook
shell à sa première exécution (`hooks_auto_accept: false`).

### Transport : webhook HA et capteurs template

Fichier : [`homeassistant/packages/claudemetre.yaml`](../homeassistant/packages/claudemetre.yaml),
installation décrite en tête du fichier. Côté WSL, le seul secret est un identifiant de
webhook, `local_only`, long et aléatoire (dans `secrets.yaml` de HA). Toutes les valeurs
partent en un appel, l'état est restauré au redémarrage de HA, et les entités ont un
`unique_id`.

- Chaque envoi porte l'état complet lu sur l'endpoint : les capteurs ne gardent rien d'un
  envoi à l'autre, et une fenêtre nulle ou absente devient « inconnu ».
- L'attribut `epoch` des capteurs de reset sert à ESPHome, qui le lit **comme texte**
  (`text_sensor: platform: homeassistant`) : un `sensor` ESPHome est un float 32 bits, qui
  ne garde un epoch qu'à 128 s près.
- Quand `resets_at` est dépassé sans nouveau déclenchement, c'est l'appareil qui passe à
  0 % / `--.--` (cahier des charges § 3) ; HA se corrige à la mesure suivante.

### Entités d'usage

| Entité | Type | Source |
| --- | --- | --- |
| `sensor.claude_usage_session` | % | `five_hour.used_percentage` |
| `sensor.claude_usage_semaine` | % | `seven_day.used_percentage` |
| `sensor.claude_reset_session` | timestamp (+ attribut `epoch`) | `five_hour.resets_at` |
| `sensor.claude_reset_semaine` | timestamp (+ attribut `epoch`) | `seven_day.resets_at` |
| `sensor.claude_derniere_mesure` | timestamp | `measured_at` |

Les `number` de calibration et de luminosité et le `select` du mode de l'afficheur sont des
entités de l'appareil ESPHome, pas de ce package.

## Activité de Claude

Deux capteurs binaires dans HA, pour le témoin CLAUDE (voir
[temoin.md](temoin.md)) et pour d'autres automatisations. Ils couvrent **toutes
les sessions en cours**, en parallèle, sous-agents en fond compris, côté Claude Code comme
côté Hermes.

| Entité | Allumée quand | Attribut |
| --- | --- | --- |
| `binary_sensor.claude_actif` | au moins un agent travaille (tour en cours, sans attente) | `agents` |
| `binary_sensor.claude_needattention` | au moins un agent attend une réponse | `demandes` |

« Attend une réponse » = une boîte de dialogue qui bloque l'agent : permission, question à
choix (`AskUserQuestion`), validation de plan (`ExitPlanMode`), formulaire MCP ; côté
Hermes, `clarify`, approbation de commande, mot de passe sudo. Une question écrite en texte
libre à la fin d'une réponse n'est **pas** comptée : pour les hooks, c'est une fin de tour
comme une autre, et on ne devine pas d'après le texte.

### Script `claudemetre-activity` (`host/claudemetre_activity.py`)

Même principe que `claudemetre-push` : bibliothèque standard seule, rien sur stdout, la
main rendue en 40 ms, le travail dans un processus détaché. Chaque hook met à jour un
registre partagé (`~/.cache/claudemetre/activity.json`, sous `flock`) : une entrée par
session et par sous-agent, avec le processus de l'agent (pid et date de démarrage), l'heure
du début du tour et les attentes en cours.

| Outil | Début de tour | Fin de tour | Attente : début / fin |
| --- | --- | --- | --- |
| Claude Code | `UserPromptSubmit`, `SubagentStart` | `Stop`, `StopFailure`, `SubagentStop`, `SessionEnd`, `PostToolUseFailure` interrompu | `PermissionRequest`, `PreToolUse` (questions), `Elicitation` / `PostToolUse(Failure)`, `PermissionDenied`, `ElicitationResult` |
| Hermes | `pre_llm_call`, `subagent_start` | `on_session_end` (chaque fin de tour : réussi, échoué ou interrompu), `subagent_stop` | `on_human_input_request` / `on_human_input_resolved` |

- Un sous-agent a sa propre entrée (`agent_id` chez Claude Code, `child_session_id` chez
  Hermes) : le `Stop` de la session principale ne l'éteint pas.
- L'attente d'une permission se lève à la fin de **cet** outil (même nom), pas d'un autre
  lancé en parallèle. Limite : elle reste allumée pendant l'exécution de l'outil approuvé,
  car aucun hook ne signale l'approbation.
- `post_compaction` (Hermes) : la compaction peut changer l'identifiant de session, l'entrée
  suit.
- Hook `PostToolUse` sur tous les outils (40 ms chacun) ; `PreToolUse` seulement sur
  `AskUserQuestion|ExitPlanMode`.

Fins jamais signalées, rattrapées par un **surveillant** détaché qui ne vit que tant que le
registre n'est pas vide (toutes les 3 s) :

- processus de l'agent disparu (kill, plantage, terminal fermé) : entrée retirée ;
- Échap ou permission refusée dans Claude Code : aucun hook, mais Claude Code écrit
  `[Request interrupted by user…]` dans le transcript ; une marque postérieure au début du
  tour le termine (seulement un bloc `text` qui commence par la marque : un résultat d'outil
  qui la cite ne compte pas) ;
- Échap avant le premier mot de la réponse : Claude Code n'écrit **rien**, le transcript
  s'arrête sur la requête (`api-request`). Si rien n'a suivi depuis 10 min
  (`UNANSWERED_AFTER`), le tour est tenu pour annulé (session principale seulement, pas les
  sous-agents) ; en pratique, le message revient dans la zone de saisie et son renvoi remet
  l'état d'aplomb bien avant ;
- aucun événement depuis 1 h (`STALE_AFTER`) : entrée abandonnée, sauf une attente de
  réponse, qui reste allumée tant que le processus vit. Une réflexion de plusieurs minutes
  sans hook ne pose pas de problème : seul le surveillant entretient l'état dans HA.

Envoi à HA : second webhook (`CLAUDEMETRE_ACTIVITY_WEBHOOK_ID`, secret
`claudemetre_activity_webhook_id`), au changement des compteurs, puis toutes les 60 s tant
que l'un d'eux est non nul. Les capteurs ont un `auto_off` de 3 min : PC éteint ou WSL
arrêté, ils s'éteignent seuls.

```json
{"active": 2, "attention": 1, "updated_at": 1793183889, "source": "hooks"}
```

Non couvert : claude.ai (web, mobile, appli), `claude -p --bare`, les profils Hermes sur
OpenRouter.

### Hooks d'activité

- Claude Code (`~/.claude/settings.json`) : `UserPromptSubmit`, `PreToolUse` (matcher
  `AskUserQuestion|ExitPlanMode`), `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`,
  `PermissionDenied`, `Elicitation`, `ElicitationResult`, `SubagentStart`, `SubagentStop`,
  `Stop`, `StopFailure`, `SessionEnd` → `~/.claude/hooks/claudemetre-activity`.
- Hermes : `pre_llm_call`, `on_session_end`, `subagent_start`, `subagent_stop`,
  `post_compaction`, `on_human_input_request`, `on_human_input_resolved`, dans
  `~/.hermes/config.yaml` et dans les profils sur Anthropic, qui reçoivent aussi le
  `post_llm_call` de l'usage. Accords dans chaque `shell-hooks-allowlist.json` ; la
  passerelle relit les hooks en 30 s environ, sans redémarrage. `hermes hooks doctor`
  vérifie le tout.

Tests `pytest` (`host/test_claudemetre_activity.py`) : tours, sessions parallèles, sous-agent
qui survit au `Stop`, attentes, interruption, processus disparu, battement, mode hook muet.

## Risques

- **Endpoint non documenté** : il peut changer. Repli : la statusline, pour le TUI seulement.
- **Login partagé avec Hermes** : `auth.adopt_external_logins: true` dans
  `~/.hermes/config.yaml` lui fait emprunter **et rafraîchir** le login Claude Code ; les
  refresh tokens sont à usage unique, et deux programmes peuvent alors se déconnecter
  mutuellement. Le script ne fait que lire, mais il subit ces déconnexions. Un login propre à
  Hermes supprimerait le conflit, et son usage compterait toujours sur le même compte.
- **Rien ne déclenche** quand ni Claude Code ni Hermes ne tournent : l'usage fait sur
  claude.ai pendant ce temps n'apparaît qu'au prochain déclenchement, et « dernière mesure »
  vieillit.

## Firmware ESPHome

`esphome/claudemetre.yaml`, avec le paquet générique du voyant `esphome/temoin.yaml` (ruban
WS2812B, effets Fixe / Respiration / Clignotement / Balayage, réglage de luminosité), qui
peut resservir aux témoins du générateur. L'appareil répond à `claudemetre.local`.

- `sensor: platform: homeassistant` pour les deux pourcentages, `text_sensor` pour les deux
  attributs `epoch` (convertis en entier dans la lambda d'affichage) ;
  `time: platform: homeassistant` pour l'heure locale.
- Lecture seule des états : pas besoin d'autoriser l'appareil à appeler des actions HA.
- Lambda d'affichage TM1637 (`--.--` si inconnu ou dépassé) ; selon le `select`
  `Afficheur mode` : `Heure de reset` (`HH.MM` en heure locale) ou `Temps restant` (`-H.MM`,
  arrondi à la minute supérieure), décompté par l'ESP32 sans le PC ; le
  reste en composants natifs.
- Jauges étalonnées en 5 points depuis HA : changer un point amène la jauge dessus pendant
  20 s, pour le régler à l'œil.

## Carte Lovelace `claudemetre-card`

Une carte personnalisée pour les tableaux de bord HA, qui reprend le look de l'objet (coque
kaki, platine noire, deux SO-45 à cadran sombre, plaquettes SESSION / SEMAINE / RÉINIT.,
visière, afficheur jaune, voyant) et lit les entités ci-dessus.

Tout est en SVG/CSS, sans image de fond : l'échelle vient de
`design/dials/dial_so45_spec.json` (mêmes graduations que les cadrans imprimés) ; coque,
platine, collerettes, plaquettes, visière et afficheur sont dessinés. **Configuration en
YAML seulement**, sans éditeur visuel.

- Un seul fichier JS, composant web natif (`customElements.define`, Shadow DOM), **sans
  dépendance ni étape de build**.
- Segments du 7 seg dessinés en SVG d'après les contours exacts du TM1637
  (`tm1637_segments.json`), segments éteints à peine visibles.
- Textes des plaquettes et des cadrans **en tracés SVG**, mêmes géométries que les cadrans
  imprimés et les plaquettes de Fusion (`so45_print.py`, `plaquettes_texte.py`) : pas de
  `@font-face`, mal pris en charge dans le Shadow DOM. Les tracés sont produits par
  `card_assets.py`, qui réécrit le bloc `ASSETS` du JS.
- Propres à la carte (absents de l'objet) : **deux-points** de l'afficheur (l'objet n'a qu'un
  point), **aiguilles rouges** et **valeur en % sous les plaquettes** SESSION et SEMAINE, atténuée avec l'afficheur quand les données sont périmées.
  Couleurs réglables par variables CSS (`--cm-needle`, `--cm-value`, `--cm-seg-on`,
  `--cm-kaki`…).
- Mêmes règles que l'appareil : aiguille qui glisse vers la valeur (transition CSS lente) ;
  séparateur qui clignote quand une heure est affichée ; reset dépassé → 0 % et `--:--` sans
  attendre HA (minuterie de 30 s), pour la session comme pour la semaine (d'où `week_reset`) ;
  capteur inconnu → aiguille au repos et `--:--`. Données périmées (`dernière mesure` trop
  ancienne ou inconnue) → afficheur atténué.
- Heure `HH:MM` dans le fuseau de HA (`hass.config.time_zone`), via `Intl.DateTimeFormat`.
- Clic sur une jauge, l'afficheur ou le voyant → fenêtre « plus d'infos » de l'entité (voyant :
  `attention` quand il est rouge, `active` sinon).
- **Voyant** : cadre kaki avec sa visière, légende CLAUDE dans un masque noir, sur la rangée des
  plaquettes SESSION / SEMAINE. Il reste à recaler sur le témoin de l'objet (carte : cadre
  40 × 18, fenêtre 27 × 10,5, avec visière ; objet : cadre 52 × 18, fenêtre 32 × 11, capitales
  de 6,64 mm, sans visière). États, comme sur l'objet : rouge qui clignote (1 s) quand
  `attention` est `on`, prioritaire ; ambre qui respire (1,6 s) quand `active` est `on` ; éteint
  sinon, y compris inconnu, indisponible ou absent. Pas d'atténuation quand les données d'usage
  sont périmées : ces capteurs ont leur propre `auto_off` de 3 min. Info-bulle : « Claude au
  travail (2 agents) », « Claude attend une réponse », « Claude au repos » ou « Activité de
  Claude inconnue ». Couleurs : `--cm-lamp-amber`, `--cm-lamp-red`, `--cm-lamp-off`. Sans
  animation si le système demande moins de mouvement.
- Configuration, avec ces valeurs par défaut :

```yaml
type: custom:claudemetre-card
entities:
  session: sensor.claude_usage_session
  week: sensor.claude_usage_semaine
  session_reset: sensor.claude_reset_session
  week_reset: sensor.claude_reset_semaine
  last_measure: sensor.claude_derniere_mesure   # null : jamais atténué
  active: binary_sensor.claude_actif            # voyant ambre
  attention: binary_sensor.claude_needattention # voyant rouge, prioritaire
stale_after: 30   # minutes
```

### Fichiers de la carte

| Fichier | Rôle |
| --- | --- |
| `homeassistant/www/claudemetre/claudemetre-card.js` | la carte, seul fichier à copier dans HA |
| `homeassistant/card-dev/card_assets.py` | réécrit le bloc `ASSETS` du JS (`uv run card_assets.py`) après une modification des cadrans, des plaquettes, de la légende du voyant ou de l'afficheur |
| `homeassistant/card-dev/preview.html` | aperçu sans HA : faux `hass` piloté par curseurs (valeur, `unknown`, `unavailable`, entité absente ; nombre d'agents et de demandes pour les deux capteurs binaires), fuseau de HA, scénarios, six cartes (clair / sombre × 320 px, 492 px, pleine largeur), journal des erreurs et des « plus d'infos » |

Aperçu, depuis la racine du dépôt :

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory homeassistant
```

puis `http://localhost:8765/card-dev/preview.html` (aussi depuis Windows, WSL étant en réseau
mirrored). Paramètres d'URL : `?scenario=Périmé` (ou un autre nom de scénario) ; `?verifier`
lance la vérification automatique, aussi accessible par le bouton « Vérifier » : chaque
scénario, deux fuseaux, le reset qui passe sans nouvel envoi de HA (attente de 31 s), les clics
« plus d'infos » et les configurations refusées, en comparant l'état lu dans chaque carte
(aiguilles, valeurs, segments allumés, atténuation, état, animation et info-bulle du voyant) à
un calcul fait indépendamment par la page. Sans navigateur à l'écran :

```sh
chromium-browser --headless=new --virtual-time-budget=45000 --dump-dom \
  "http://127.0.0.1:8765/card-dev/preview.html?verifier" | grep -o "<title>[^<]*"
```

(`<title>OK` ou `<title>ÉCHEC n`, détail dans le journal de la page).

### Déployer la carte

Dans HA : le fichier va dans `<config>/www/claudemetre/claudemetre-card.js`, déclaré comme
ressource `/local/claudemetre/claudemetre-card.js` de type module (Paramètres > Tableaux de bord
> Ressources, en mode avancé). Ajouter `?v=N` à l'URL de la ressource à chaque mise à jour pour
contourner le cache du navigateur.

La config de HA est accessible par le partage Samba (`HA_SAMBA` et `HA_SAMBA_USER` de
`prive.env`), déjà ouvert dans la session Windows : depuis WSL, passer par `cmd.exe` (le
dossier est aussi un dépôt git). Copie de la carte :

```sh
. ./prive.env
cp homeassistant/www/claudemetre/claudemetre-card.js "$WIN_TEMP/claudemetre/"
cd /mnt/c && cmd.exe /c "copy /Y %TEMP%\claudemetre\claudemetre-card.js $HA_SAMBA\www\claudemetre\"
```

Les tableaux de bord sont en mode *storage* : ressources et cartes se déclarent dans l'interface,
pas en éditant `.storage/` (HA le réécrit depuis sa mémoire).
