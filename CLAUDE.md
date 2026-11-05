# Claudemètre

Objet mural (planche PC en bois) qui affiche l'usage du forfait Claude
(Pro/Max) et l'activité des agents : deux jauges analogiques à aiguille, un
afficheur 7 segments et un témoin lumineux CLAUDE, pilotés par un ESP32 en
WiFi.

Inspiré de [Clawdmeter](https://github.com/HermannBjorgvin/Clawdmeter), mais
refait à notre façon : pas de Bluetooth, pas d'écran, pas d'appli desktop.

Firmware sous EspHome + liaison HomeAssistant.

## Ce que l'objet affiche

| Élément | Donnée | Source |
| --- | --- | --- |
| Jauge gauche | % utilisé de la session | `five_hour` (5 h glissantes) |
| Jauge droite | % utilisé de la semaine | `seven_day` |
| Afficheur 7 seg | heure de reset de la session (`HH.MM`) ou temps restant (`-H.MM`), au choix depuis HA | `five_hour.resets_at` |
| Témoin CLAUDE | agent au travail (ambre qui respire), agent qui attend une réponse (rouge qui clignote, prioritaire) | `binary_sensor.claude_actif`, `binary_sensor.claude_needattention` |

## Principes directeurs (non négociables)

- **Le plus simple possible, épuré.** Le moins de composants possible.
  Cible : ESP32 + 2 voltmètres + 1 module 7 seg + témoin CLAUDE + câble USB,
  rien d'autre si on peut l'éviter. Toute pièce ajoutée doit se justifier.
- **Style instrument de bord** : coque kaki, platine noire, cadrans sombres,
  plaquettes noires à texte blanc. L'objet s'accroche sur la planche murale
  en bois qui porte le PC.
- **Fabrication** : tout le boîtier est imprimé en 3D, le reste vient du
  commerce (voltmètres, afficheur, ESP32, connecteurs, visserie). Assemblage
  par vis M3 sur inserts laiton, et par collage.
- **WiFi uniquement.** Le PC (Claude Code) pousse les données vers HA.
  l'ESP32 sous EspHome recupere les données depuis HA sur le réseau local.
- **ESPHome + Home Assistant** : l'objet est un appareil ESPHome ; les
  valeurs d'usage (session %, semaine %, heures de reset) existent comme
  capteurs dans Home Assistant, réutilisables ailleurs.
- **Token OAuth de Claude Code en lecture seule** : ne jamais le rafraîchir ni
  le réécrire (Claude Code en est propriétaire ; un refresh concurrent peut le
  déconnecter).

## Architecture

```
WSL2 : hooks Claude Code + Hermes ──► lecture de l'endpoint d'usage OAuth ──webhook──► Home Assistant
                                      │
                                      ▼
            ESP32 sous ESPHome ── capteurs visibles dans Home Assistant
              ├─ PWM (ledc) ──► 2 voltmètres (pleine échelle vers 3 V)
              ├─ TM1637 ──────► 7 seg (heure de reset de la session ou temps restant)
              └─ WS2812B ─────► témoin CLAUDE (activité des agents)
```

- Source : l'**endpoint d'usage OAuth**, lu par un script que lancent un hook global de Claude Code et un
  hook de Hermes (pas de démon). Il voit tout l'usage du compte (TUI,
  `claude -p`, Hermes, claude.ai) ; la statusline ne voit que le TUI, et les
  hooks ne reçoivent aucun chiffre.
- Liaison vers ESPHome : webhook Home Assistant → capteurs template, lus par
  l'appareil.
- WSL2 est en `networkingMode=mirrored` (`%USERPROFILE%\.wslconfig`) : WSL voit
  directement le LAN (`LAN` de `prive.env`).
- Sens des flux : c'est le PC qui pousse ; l'ESP32 n'interroge jamais
  Anthropic (il n'a pas le token).
- Détails : [docs/source-donnees.md](docs/source-donnees.md) et
  [docs/cahier-des-charges.md](docs/cahier-des-charges.md). Partie
  logicielle : [docs/logiciel.md](docs/logiciel.md).

## Arborescence

```
esphome/    firmware ESPHome : claudemetre.yaml (l'appareil), temoin.yaml (paquet générique
            du voyant WS2812B) ; secrets.yaml (wifi_ssid, wifi_password,
            api_encryption_key) et .esphome/ hors dépôt (.gitignore)
host/       scripts côté WSL (hooks claudemetre-push et claudemetre-activity)
homeassistant/  package HA (packages/claudemetre.yaml), carte Lovelace (www/claudemetre/),
                aperçu et générateur de la carte (card-dev/)
maquette/   page 3D assemblé / éclaté (three.js, sans build) et son modèle claudometre.glb
            (`uv run pack.py`), publiée sur GitHub Pages : voir maquette/README.md
docs/       cahier des charges, notes techniques
  en/       version anglaise du README et des docs
design/     maquettes et gabarits
  references/grabcad.md            pages GrabCAD des modèles tiers de references/
  references/so45/                 modèle 3D du voltmètre SO-45 (STEP, F3D) + cotes (README),
                                   cadran d'origine mesuré (cadran_photo.jpg, cadran_redresse.jpg)
  references/lp16/                 embases CNLINKO LP-16 2 pôles et USB-C (STEP, IGES GrabCAD) + cotes (README), pour Fusion
  references/mrd076a/              carte à borniers MRD076A avec l'ESP32 enfiché (STEP GrabCAD) + cotes (README), pour Fusion
  references/tm1637/               modèle 3D de l'afficheur TM1637 0,56" (STEP GrabCAD), contour des
                                   segments (`uv run step_to_segments.py`) + cotes (README)
  fusion/                          design Fusion 360 : notes et cotes (README), 3MF et leurs scripts
  dials/so45_print.py              dessin du cadran SO-45, repris par Fusion et la carte : `uv run so45_print.py`
                                   (cotes dans dials/dial_so45_spec.json)
  plaquettes/plaquettes_texte.py   textes des plaquettes (DXF pour Fusion) : `uv run plaquettes_texte.py`
  fusion/scripts/                  scripts de construction du design Fusion (exécutés par MCP, voir README)
  fusion/print/                    3MF des cadrans à imprimer, une pièce par couleur (`uv run cadran_3mf.py`, skill `cadrans-3mf`) ;
                                   coque, platine, patron de perçage, plaquettes, visière, plaques de flanc et clips (`uv run coque_3mf.py`, `platine_3mf.py`, `patron_3mf.py`, `plaquettes_3mf.py`,
                                   `visiere_3mf.py`, `plaques_3mf.py`, `clips_3mf.py`)
  cablage/index.html               schéma de câblage (artifact privé, republier sur la même URL)
  temoin/                          preset du témoin CLAUDE (claude.json) et export/ du générateur
                                   (skill `temoin-lumineux`, docs/temoin.md)
  blender/                         scène de la maquette `jj_fusion` (cm_lib.py, variants6.py)
  blender/render.sh <variante> [preview|final]   rendu via Blender 5.2 Windows
  blender/anim.sh <variante> [preview|final]     vidéo du voyant (MP4 dans renders/)
  fusion/blender/                  maillages du design pour la maquette à jour `jj_fusion`
                                   (`scripts/export_blender.py`, docs/maquettes.md)
  gallery/                         page de la maquette à jour, artifact privé (jj_fusion.html, img/)
  renders/                         rendus finaux ; renders/preview/ = brouillons
  fonts/                           Barlow Condensed et Semi Condensed (licence OFL)
```

## Conventions

- Échanges et documentation en **français** ; identifiants de code en anglais.
- Firmware : **ESPHome**, avec le framework **ESP-IDF**
  (`esp32: framework: type: esp-idf`), pas Arduino. Lambdas C++ seulement
  là où les composants natifs ne suffisent pas. Valider et compiler avec le
  skill global `esphome` (venv `~/esphome`, script `esph.sh`) ; téléverser
  seulement sur demande.
- Secrets (WiFi, clé API ESPHome, jeton Home Assistant) dans `secrets.yaml`
  hors du dépôt.
- Matériel : carte **diymore ESP32-S3-DevKitC-1 N16R8** (Amazon
  B0F3XMYYQY) : 16 Mo de flash, PSRAM octale (GPIO33-37
  pris), enfichée sur une carte à borniers **MRD076A** (Amazon B0FKBLR2KF).
  Broches : GPIO4 / GPIO5 jauges session / semaine (PWM), GPIO6 / GPIO7
  TM1637 CLK / DIO, GPIO15 ruban du voyant (en tête de `esphome/claudemetre.yaml`).
- Impression 3D du boîtier : **tout en PETG**, sauf les plaquettes : PLA noir,
  texte en PLA blanc.
- **Platine déjà imprimée** : ne plus la modifier ; toute évolution
  du design reste compatible avec elle (188 × 90, vis à x = ±88, z = ±39).
- Visserie M3 selon le stock : FHC à partir de M3×12 seulement,
  CHC en 6, 8, 10, 12, 16 et plus. Détail dans
  [docs/cahier-des-charges.md](docs/cahier-des-charges.md).
- Fusion : charger le skill `fusion360` avant d'utiliser le serveur MCP.
- **Maquette 3D** (`maquette/`) : `.github/workflows/pages.yml` la publie sur GitHub Pages à chaque
  push sur `main` qui la touche, sans la régénérer. Si le design a changé, la mettre à jour **juste
  avant de pousser sur la remote** (`maquette/README.md`), pas pendant le développement.
- Témoins lumineux : pour refaire le témoin CLAUDE ou en créer d'autres,
  toujours passer par le skill `temoin-lumineux` (commande `temoin`). Le
  preset `design/temoin/<nom>.json` est la seule source : on le modifie, on
  contrôle, on régénère ; jamais de retouche des fichiers de
  `design/temoin/export/` ni de témoin dessiné à la main dans Fusion.
- **Artefacts** : `ARTEFACTS.md`, à la racine et hors dépôt (`.gitignore`), liste
  les pages privées claude.ai du projet et leur source. On les garde toutes, et
  leurs liens ne vont que là, jamais dans un fichier suivi par Git.
- **Données locales** : `prive.env`, à la racine et hors dépôt (`.gitignore`), regroupe
  les chemins et adresses propres au poste : Home Assistant, LAN, `%TEMP%` de Windows,
  dépôt vu de Windows, Blender, projet Fusion. Modèle : `prive.exemple.env`. Les docs et les scripts y renvoient (`. ./prive.env`
  dans le shell, `design/fusion/prive.py` en Python) ; ces valeurs ne vont que là, jamais
  dans un fichier suivi par Git.

## Référence visuelle

Le design Fusion `claudometre` fait foi. Sa maquette à jour est `jj_fusion`
(`design/renders/jj_fusion.png`, [docs/maquettes.md](docs/maquettes.md)).

## État

Objet terminé et en service, posé provisoirement sur le bureau, à accrocher ensuite sur
la planche. Côté WSL, Home Assistant, carte Lovelace et firmware en service.

Ce qui reste à faire et les questions ouvertes sont listés en fin de
[docs/cahier-des-charges.md](docs/cahier-des-charges.md) : les mettre à jour à chaque
décision.
