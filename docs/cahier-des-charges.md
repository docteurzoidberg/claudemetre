# Cahier des charges

## 1. Style

- Instrument de bord, pour la planche murale en bois du PC : coque kaki,
  platine noire, cadrans sombres, plaquettes noires à texte blanc.
- Deux **jauges analogiques à aiguille** (voltmètres de tableau détournés).
- Un **afficheur 7 segments** pour l'heure de reset de la session ou le temps restant.
- Un **témoin lumineux CLAUDE** (légende éclairée) pour l'activité des agents :
  ambre qui respire au travail, rouge qui clignote quand l'un d'eux attend une
  réponse.
- Cadrans **réimprimés en 0-100 %** à la place de l'échelle en volts, en
  **multi-filament** sur la Snapmaker U1 (4 têtes, buse 0,4) : forme exacte de
  la plaque d'origine, vissés à sa place sur les deux piliers Ø 5. 2 mm
  d'épaisseur, couleurs sur 0,8 mm (une couleur par corps), fond derrière sauf
  des lamages autour des piliers, face à 0,8 mm de l'appui. Graduations tous les
  5 %, chiffrées tous les 25 %, zone rouge 80-100 %, « % · 5 H » / « % · 7 J »
  en haut du cadran. Le nom de l'instrument (SESSION / SEMAINE) est sur une
  plaquette vissée sous la jauge. Dessin : `design/dials/so45_print.py`.
- Référence visuelle : le design Fusion `claudometre` (voir CLAUDE.md).

## 2. Matériel

### Nomenclature

| Pièce | Qté | Remarque |
| --- | --- | --- |
| Carte ESP32-S3-DevKitC-1 N16R8 (diymore) | 1 | Amazon B0F3XMYYQY |
| Carte à borniers MRD076A | 1 | l'ESP32 s'enfiche dessus, câblage vissé sans soudure ; Amazon B0FKBLR2KF ; cotes : `design/references/mrd076a/README.md` |
| Voltmètre analogique 0-5 V « SO-45 » | 2 | ramené à ~3 V pleine échelle par une résistance interne (voir plus bas) |
| Module 7 seg 4 chiffres 0,56" à points décimaux (TM1637), jaune | 1 | AliExpress 1005001970566474 ; cotes : `design/references/tm1637/README.md` |
| Témoin CLAUDE : tronçon de ruban WS2812B à 144 LED/m (4 LED), diode 1N400x, 2 FHC M3×8, 2 inserts M3 | 1 | pièces imprimées par le générateur, voir [temoin.md](temoin.md) |
| Câble / alim USB 5 V | 1 | |
| Porte-fusible de panneau 5 × 20 et fusible | 1 | sur `plaque_bossage_fusible`, protège l'arrivée 12 V ; cotes : `design/references/fusible/README.md` |

Rien d'autre si possible : ni potentiomètre d'ajustage, ni carte de filtrage.

### Pilotage des jauges

- Un voltmètre à cadre mobile est un galvanomètre avec une résistance série, qui
  seule fixe le calibre. Une sortie GPIO de 3,3 V n'amènerait un 0-5 V qu'aux
  deux tiers de sa course.
- **Pleine échelle ramenée vers 3 V** : **6,2 kΩ en parallèle sur `R_s`**
  (résistance série interne), sur les deux voltmètres, à l'intérieur du boîtier.
  Rien de visible, aucune pièce externe. Le 100 % imprimé tombe vers 2,93 et
  2,95 V. Mesures et calculs :
  [design/references/so45/README.md](../design/references/so45/README.md).
- **PWM (LEDC) directement sur le voltmètre**, à 25 kHz, au-dessus de l'audible :
  l'inertie du cadre mobile en fait la moyenne. L'ESP32-S3 n'a pas de DAC.
- Pas de résistance de protection externe : la résistance série interne limite
  déjà le courant (≈ 1,1 × pleine échelle à 3,3 V, sans danger pour le cadre
  mobile). Jamais de 5 V sur un GPIO.
- **Calibration logicielle**, sans trimmer : table de correspondance par jauge
  (0/25/50/75/100 %), réglable depuis Home Assistant (entités `number`
  ESPHome), qui corrige aussi la non-linéarité des cadrans. L'ESP peut dépasser
  les traits imprimés aux deux bouts : en haut, ≈ 12 % au-delà du 100 %
  (≈ 5 % au pire) ; en bas, le PWM ne descend pas sous zéro, donc la vis du zéro
  (en façade) met l'aiguille au repos un peu sous le 0 % imprimé, et le 0 %
  logiciel est un petit rapport cyclique.
- Format du SO-45 : collerette **carrée 46,8 × 46,8 × 4,65 mm** à 4 trous Ø 4
  (entraxe 37 mm), lunette **Ø 45** en saillie de 4,65 mm, fenêtre **Ø 38,8 en
  « D »**, corps **Ø 45 × 24,4 mm**, 2 bornes M4 de 8,5 mm.

### Afficheur 7 segments

- **TM1637 4 chiffres à points décimaux** (un point entre chaque chiffre, pas de
  deux-points) : 2 fils (CLK, DIO), alimenté en 3,3 V,
  luminosité réglable, composant `tm1637` natif d'ESPHome. Ce n'est pas un vrai
  I²C (pas d'adresse, protocole propre) : deux GPIO quelconques, sans partage
  avec un bus I²C.
- Affiche **l'heure de reset de la session** (`14.32`) ou **le temps restant avant
  ce reset** (`-2.07`), au choix depuis HA.
- Module 0,56" à segments jaunes, PCB de 66 × 27,2 mm, 4 trous M3 (Ø 3,3) à
  l'entraxe 60 × 21,5. Fils sur un pin header coudé, tourné vers l'intérieur de
  l'afficheur : le PCB passe à 0,9 mm du SO-45 de droite.

### Carte ESP32

- **diymore ESP32-S3-DevKitC-1 N16R8** : 16 Mo de flash, 8 Mo de PSRAM octale
  (GPIO33-37 pris), deux USB-C, brochage de la DevKitC-1 d'Espressif.
- **Carte à borniers MRD076A** : 73,6 × 84,7, 20,5 mm d'empilement avec l'ESP32.
- **Support** : trois clips imprimés, sans vis, collés dans des logements du fond
  de la coque (1,5 mm de profondeur sur un fond de 3 mm). Carte debout, centrée,
  antenne en haut. Câblage par les borniers des côtés seulement, passage de câbles
  possible sous la carte. Voir `design/fusion/README.md`.
- Broches (firmware `esphome/claudemetre.yaml`), à la suite sur le connecteur de
  gauche : GPIO4 jauge session, GPIO5 jauge semaine, GPIO6 TM1637 CLK, GPIO7
  TM1637 DIO, GPIO15 ruban du voyant.

### Alimentation et connecteurs

- Alimentation USB pour l'instant, puis 12 V ramené à 5 V par une alim ATC, avec
  le connecteur LP-16 2 pôles. Le 5 V arrive sur le bornier `5V` : la carte à
  borniers n'a pas de prise d'alimentation, et le port USB de l'ESP32 n'est pas
  accessible dans le boîtier.
- Connecteurs sur des plaques amovibles, une dans chaque flanc de la coque, plaque
  pleine du côté inutilisé : changer de connecteur, c'est refaire une plaque, pas
  la coque. Le câble passe par l'un ou l'autre flanc.
- `plaque_flanc` est la plaque générique, pleine, qui fixe l'interface commune.
  `plaque_bossage` porte le LP-16, incliné de 30° vers le haut.
  `plaque_bossage_fusible` porte le LP-16 et un porte-fusible qui protège l'arrivée
  12 V, axes parallèles à 45°. Voir `design/fusion/README.md`.
- Chaque plaque est un composant complet, avec ses connecteurs et leur visserie.
  Toutes restent dans le design : on affiche celle qu'on veut et on masque les autres.

### Fabrication

- Boîtier tout imprimé en 3D, le reste vient du commerce (voltmètres, afficheur,
  ESP32, connecteurs, visserie).
- Jauges : on garde la collerette noire d'origine du SO-45.
- Assemblage : **vis M3 et inserts laiton** à chaud partout, complétés par du
  collage (visière, clips de la carte). Modèles de quincaillerie dans le dossier
  Fusion `claudometre/models/`.
- Police des cadrans : **Barlow Condensed SemiBold**, texte blanc incrusté dans le
  fond noir, imprimé face contre le plateau.
- Plaquettes : **Barlow Semi Condensed Medium**, capitales de **3 mm**,
  identiques sur les trois, plaquettes de 40 × **8** × **1,8 mm** (axe des vis à
  4 mm de chaque bord). Trait de 0,54 mm (fût) et 0,48 mm (barre) : sous 0,46 mm,
  le trancheur perd des morceaux de lettres. Point de RÉINIT. dessiné à part,
  Ø 0,9. À 1,8 mm, il reste 0,3 mm de matière sous le cône de la fraisure : c'est
  la limite.
- Visière de l'afficheur imprimée à part et collée dans une rainure de la platine,
  qui s'imprime face avant contre le plateau.
- Matière : **tout le boîtier en PETG** (coque, platine, visière, plaques de flanc,
  clips, témoin CLAUDE), sauf les plaquettes : PLA noir, texte en PLA blanc.
- Platine **déjà imprimée** : ne plus la modifier.
- Coque en une pièce, dos au plateau. À surveiller au tirage : les ponts d'environ
  70 et 84 mm des fenêtres et des feuillures, pour l'ajustement des plaques (jeu de
  0,15 mm).
- Visserie M3 selon le stock : FHC à partir de M3×12 seulement, CHC en 6, 8, 10,
  12, 16 et plus.

  | Emplacement | Vis | Qté |
  | --- | --- | --- |
  | Platine sur la coque | FHC M3×12 | 4 |
  | Plaquettes | FHC M3×12 | 6 |
  | Plaques de flanc | CHC M3×6, tête à moitié noyée | 8 |
  | Connecteur LP-16 sur `plaque_bossage` ou `plaque_bossage_fusible` | FHC M3×12, dans 4 inserts M3 | 4 |
  | Circuit de l'afficheur | CHC M3×6 | 4 |
  | Collerettes des SO-45 | CHC M3×12 | 8 |
  | Témoin CLAUDE | FHC M3×8, fin de stock (le générateur annonce M3×10) | 2 |

  Les perçages des plaques de flanc restent borgnes : traversants, une vis longue
  toucherait la vis de platine, à la même hauteur.
- Accroche murale : le boîtier tient par gravité sur deux vis à bois à tête
  saillante, à 116 mm d'entraxe, par deux **trous de serrure** qui traversent le
  fond de la coque, à la verticale des SO-45. Une fois accrochées, les vis sont à
  mi-hauteur de la coque. Un patron imprimé sert à marquer les perçages.

## 3. Logiciel

### Principes

- **ESPHome** sur l'ESP32, framework **ESP-IDF**.
- Valeurs d'usage exposées comme capteurs dans **Home Assistant**, réutilisables
  ailleurs (automatisations, tableaux de bord).
- Les chiffres couvrent **tout l'usage du compte** : TUI, `claude -p` lancé par
  d'autres outils, Hermes (API directe avec le login Claude Code), claude.ai.
- Source : l'**endpoint d'usage OAuth**, lu par un script lancé par des hooks
  (Claude Code, Hermes), sans démon, avec le token en lecture seule. Voir
  [logiciel.md](logiciel.md) et [source-donnees.md](source-donnees.md).

### Réseau

- **WiFi uniquement** (pas de Bluetooth, contrairement à Clawdmeter).
- WSL2 en mode `mirrored` : WSL joint directement le LAN, Home Assistant et l'ESP32.
- WSL pousse vers HA par webhook ; HA en fait des capteurs template ; l'appareil
  les lit par la plateforme `homeassistant`. L'objet dépend donc de HA.

### Entités ESPHome / Home Assistant

| Entité | Type | Unité |
| --- | --- | --- |
| Usage session | sensor | % |
| Usage semaine | sensor | % |
| Reset session | sensor (timestamp) | — |
| Reset semaine | sensor (timestamp) | — |
| Dernière mesure | sensor (timestamp) | — |
| Claude actif | binary_sensor | — |
| Claude attend une réponse (`claude_needattention`) | binary_sensor | — |
| Calibration jauges | number × 5 par jauge | % PWM |
| Luminosité afficheur | number | 0-7 |
| Mode afficheur | select | Heure de reset, Temps restant |
| Luminosité voyant | number | % |

Fenêtre absente = valeur inconnue, ce n'est **pas** 0 %.

### Comportement de l'appareil

- Heure : `time: homeassistant`, fuseau `Europe/Paris`.
- Démarrage : aiguilles à 100 % puis à 0 %, voyant ambre puis rouge. Sur l'afficheur,
  un trait fait le tour et s'allonge jusqu'à fermer le pourtour, puis `--.--` jusqu'aux
  premières données.
- Aiguilles qui glissent vers la nouvelle valeur (pleine échelle en ≈ 2,5 s), pour
  un rendu mécanique.
- Usage inconnu : aiguille au repos.
- Heure de reset passée : aiguille à 0 sans attendre le PC, et `--.--` sur
  l'afficheur pour la session. Si le reset tombe pendant que l'objet tourne, la
  dernière valeur clignote d'abord 5 s à pleine luminosité.
- Point entre le 2e et le 3e chiffre, qui clignote quand une heure ou un temps
  restant est affiché.
- Temps restant : `-H.MM`, arrondi à la minute supérieure (`-0.01` jusqu'au reset,
  jamais `-0.00`). Le mode choisi survit à un redémarrage.

## 4. Questions ouvertes

- [ ] Accrocher l'objet sur la planche, après avoir mesuré la tête et la tige des
      vis (`accroche_tete_d`, `accroche_tige_d`, 8 et 4 mm provisoires) ; le patron
      est à imprimer ensuite, car ses trous suivent ces valeurs.
- [ ] Alimentation 12 V : alim ATC et LP-16. Confirmer la fixation M3 sur la pièce
      reçue avant d'imprimer `plaque_bossage`.
- [ ] `plaque_bossage_fusible` : confirmer sur les pièces le filet du porte-fusible,
      l'écrou et le tranchage du tube, puis faire ses 3MF.
- [ ] Schéma de câblage (`design/cablage/index.html`) à reprendre pour la carte à
      borniers : il décrit encore des fils soudés sur J1.
- [ ] Carte Lovelace à recaler sur l'objet : voyant (cadre 52 × 18, fenêtre 32 × 11),
      forme des cadrans et afficheur, qui a un point et non un deux-points
      (`card_assets.py`, puis redéploiement dans HA).
- [ ] Afficheur modélisé avec le deux-points du STEP (design Fusion, rendus Blender,
      maquette 3D) : le module de l'objet n'a que des points.
- [ ] Carte Lovelace : elle montre toujours l'heure de reset, sans suivre le mode de
      l'afficheur de l'objet.
- [ ] Comportement sur l'objet en cas de données périmées ou de WiFi perdu : rien
      n'est signalé pour l'instant (la carte Lovelace atténue l'afficheur).
- [ ] Mode nuit (luminosité du 7 seg selon l'heure, pilotable depuis HA) ?
- [ ] Login dédié pour Hermes, pour ne plus partager celui de Claude Code ?
- [ ] `jauge_appui` à mesurer dans `claudometre` (niveau du haut des piliers, 4 mm
      posés à l'œil) : sans effet sur l'objet, seulement sur le modèle.
