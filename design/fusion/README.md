# Design Fusion `claudometre`

Le design Fusion fait foi pour la forme et les cotes de l'objet. Il est dans le dossier
`claudometre/` du projet Fusion (`FUSION_PROJET` de `prive.env`). Les scripts qui l'ont construit sont
dans `scripts/` (ordre et rôle dans `scripts/README.md`).

## Dans le cloud Fusion

| Fichier | Contenu |
| --- | --- |
| `claudometre` | le design principal (assemblage) |
| `fond-jauge` | **modèle** des cadrans imprimés (`scripts/fond_jauge.py`), d'après la plaque du cadran d'origine du SO-45 : corps `plaque_origine` à plat sur XY, face visible vers +Z, épaisseur `ep_cadran` (0,5 mm, à mesurer) ; esquisse `reperes` (axe de l'aiguille, ligne de base et débattement de l'échelle d'origine, fenêtre du modèle GrabCAD, bord du masque relevé sur photo) ; canevas `photo_redressee` dessous. Composant `fond` : le cadran imprimé sans couleurs, en position d'usage, appui sur les piliers à z = 0, face `ep_face` au-dessus, renfort `ep_dos` dessous, lamages Ø `d_pilier + 2 * jeu_pilier` ; corps `pilier_repere_*` en repère, `plaque_origine` masquée. Paramètres favoris (`ep_face`, `ep_dos`, `prof_couleur`, `d_pilier`, `jeu_pilier`, `r_plaque`, `entraxe_trous`), transmis aux variantes ; `r_plaque` (20,2) et `entraxe_trous` (31,02) pilotent l'esquisse `plaque` et les cercles de `lamages` et `piliers`. Design en **Hybrid** |
| `fond-jauge-session`, `fond-jauge-semaine` | les cadrans à imprimer, **dérivés** de `fond-jauge` (fonction Dériver : composant `fond` et paramètres favoris, suffixés `_Ref`), puis couleurs par `variante()` : poches `incruste_<couleur>` dans le fond dérivé, **un composant par couleur** (`echelle`, `zone`, `texte`, un corps par morceau, à fleur de face sur `prof_couleur_Ref`, apparence « PLA <couleur> ») |
| `claude` | témoin CLAUDE, venu du générateur (voir [docs/temoin.md](../../docs/temoin.md)) |
| `support carte esp - rteverse` | les trois clips de la carte à borniers, sans vis : `clip_aile`, `clip_aile_miroir` et `clip_milieu`, posés côte à côte pour l'impression, pas à leur place de montage. Modélisés à l'échelle 10 et ramenés à 1:1 par la fonction `echelle 1-1` (× 0,1) en fin de timeline : les esquisses restent à l'échelle 10. Cotes : 88,1 de long, 12,7 de haut, 12,5 de large (ailes) et 8 (milieu) ; logement de 84,7 entre crochets, circuit posé à 6 du fond, 1,7 sous les crochets |
| `models/voltmetre_SO-45` | envoyé depuis le `.f3d` d'origine : 4 corps, paramétrique. Unités mm, **façade vers +Y** (lunette à y = +9,3, bornes à y = -32,9), axe de la jauge sur Y à x = z = 0 |
| `models/afficheur_TM1637_056` | envoyé depuis le STEP : corps à plat, sans composants, segments passés au **jaune** du vrai module, connecteur coudé retiré. Origine au centre de la face avant de l'afficheur, **façade vers +Z** (face à z = 0, dos jusqu'à z = -12) |
| `models/mrd076a_esp32_s3` | envoyé depuis le STEP (`../references/mrd076a/`) : carte à borniers avec l'ESP32 enfiché, 8 composants, 922 corps. Unités mm, origine au milieu d'un petit bord, sur le dos du circuit, composants vers +Z |
| `models/connecteur_LP-16_2poles`, `models/connecteur_LP-16_USB-C` | embases LP-16 (`../references/lp16/`). Le 2 pôles est posé sur `plaque_bossage` et `plaque_bossage_fusible`, l'USB-C n'est pas utilisé |
| `models/porte_fusible_5x20` | envoyé depuis le STEP (`../references/fusible/`) : 7 corps, unités mm, axe sur Z, +Z vers le capuchon, origine près de son sommet. Posé sur `plaque_bossage_fusible` |
| `models/insert_chaud_M3` | insert laiton M3 Ø5 × 4, origine sur la face d'entrée, corps vers -Z |
| `models/vis_FHC_M3x12` | vis fraisée M3×12, origine sur le dessus de la tête |
| `models/vis_CHC_M3x12`, `models/vis_CHC_M3x6` | vis CHC M3, origine sous la tête |

Les modèles de `models/` s'insèrent dans `claudometre` comme composants externes (Insérer
dans la conception courante).

## Le design `claudometre`

Repère : **origine au centre de la façade de la coque**, X à droite, Z en haut, **+Y vers
le mur** ; la vue « Avant » de Fusion montre la façade. Ce sont les axes de la maquette
Blender (profondeur positive vers le mur). Toutes les cotes sont des paramètres utilisateur
(`coque_*`, `rebord_*`, `ouv_*`, `vis_*`, `insert_*`, `platine_*`, `jauge_*`, `aff_*`,
`plaq_*`…).

| Composant | Contenu |
| --- | --- |
| `coque` | PETG kaki, imprimée sur le dos : 200 × 96 × 40, parois 2,5, fond 3. Rebord avant de 3 mm (ouverture 168 × 76) qui porte la platine, chanfrein à 45° dessous, 4 piliers d'angle avec logements d'inserts M3 (Ø4,2 × 4,5, puis Ø3,4 jusqu'à 10) |
| `platine` | PETG noir, face avant sur le plateau : 188 × 90 × 3. Passages Ø46 des SO-45, fenêtre 50,8 × 19,6 de l'afficheur, découpe du témoin, 4 fraisures M3 aux coins ; au dos, bossages d'inserts pour les jauges (Ø8 × 5), l'afficheur (Ø6,4 × 4,7, le circuit vient s'y poser) et les plaquettes (Ø8 × 3). **Déjà imprimée : ne plus la modifier** |
| `plaquette_session` / `_semaine` / `_reinit` | PLA noir, 40 × 8 × 1,8, deux fraisures M3 à 32 d'entraxe, axe des vis à 4 de chaque bord. Chaque plaquette est modélisée autour de sa propre origine et placée par liaison (`jo_plaquette_*`). Texte en **Barlow Semi Condensed Medium**, capitales de 3 mm, incrusté sur 0,6 mm : corps `texte_*` séparés (un par lettre), en PLA blanc. Contours générés par `../plaquettes/plaquettes_texte.py` (DXF) |
| `visiere` | PETG kaki, imprimée à part, debout sur son chant arrière (sans support), puis collée dans une rainure en U de la platine (1,5 mm de profondeur, 0,1 mm de jeu par côté). Toit de 12 mm de saillie, avant des joues en pente jusqu'à 4 mm en bas (`visiere_P_bas`) |
| `voltmetre_SO-45` (×2) | centres à x = ±58, z = +8, collerette devant la platine |
| `afficheur_TM1637_056` | centre à x = 0, z = +11, derrière sa fenêtre |
| `fond-jauge-session` / `fond-jauge-semaine` | cadrans à imprimer, insérés comme composants externes (« Mettre à jour » après une nouvelle version). Chacun est lié à son SO-45 (`cadran_session`, `cadran_semaine`) : origine du cadran sur l'axe de la jauge, à `jauge_appui` du dos de la collerette |
| `claude` | témoin CLAUDE, centré à x = 0, z = −26, sans liaison |
| `mrd076a_esp32_s3`, `clip_aile`, `clip_aile_miroir`, `clip_milieu` | carte à borniers et ses clips, voir « Support de la carte à borniers » |
| `plaque_flanc`, `plaque_bossage`, `plaque_bossage_fusible` | plaques de flanc, chacune avec ses connecteurs et leur visserie, voir « Interface des plaques de flanc » |
| `patron` | patron de perçage, voir « Accroche murale » |
| `visserie` | 30 inserts M3 ; 10 FHC M3×12 (platine → coque 4, plaquettes 6) ; 8 CHC M3×12 (collerettes) ; 12 CHC M3×6 (plaques de flanc 8, circuit de l'afficheur 4). Chacun est lié au centre de son perçage. Vis visibles en oxyde noir. La visserie d'un connecteur est dans le composant de sa plaque |

Jeux contrôlés : corps des SO-45 à 0,5 mm des passages, afficheur à 0,3 mm de sa fenêtre,
circuit de l'afficheur à **0,9 mm** du SO-45 de droite. Le connecteur coudé du modèle, qui
touchait ce SO-45, est retiré : le vrai module a un pin header coudé tourné vers l'intérieur
de l'afficheur.

Les perçages des inserts de l'afficheur s'arrêtent sous l'insert (la vis M3×6 n'en sort
pas) : ils ne croisent pas la rainure de la visière.

`jauge_appui` (4 mm, à mesurer) est le niveau du haut des piliers dans le repère du SO-45 :
face du cadran à 4,8, soit 4,5 sous l'avant de la lunette. Le modèle GrabCAD n'a pas
d'intérieur : le fond plein de sa fenêtre est à 4,65 et le dos du cadran y entre (interférence
sans objet). `Body2`, sa plaque blanche en « D » à 7,4-8,2, reste masqué : il cacherait le
cadran.

## Fichiers à imprimer

Tous dans `print/`. Après une modification : `scripts/export_<pièce>.py` dans Fusion, puis
`uv run <pièce>_3mf.py` ici. Pour les cadrans, voir plus bas.

| Fichier | Matière | Position | Temps, masse |
| --- | --- | --- | --- |
| `coque.3mf` | PETG kaki (filament 4), supports en PETG noir (filament 3) | dos au plateau, supports en arbre | 4 h 23, 122 g |
| `plaquettes.3mf` | PLA (gabarit `u1-4pla`), noir (filament 4) et blanc (filament 1) | face visible sur le plateau | 11 min, 2,2 g de noir, 0,4 g de blanc |
| `visiere.3mf` | PETG kaki (gabarit `u1-petg`, filament 4, couleur de la coque enregistrée dans Orca) | debout sur son chant arrière, sans support ni bordure | 14 min, 2,8 g |
| `platine.3mf` | PETG noir (filament 3) | face avant sur le plateau, sans support | 1 h 07, 32 g |
| `plaque_flanc.3mf` | PETG noir (filament 3) | face d'appui sur le plateau, sans support | 13 min, 7,2 g |
| `plaque_bossage.3mf` | PETG kaki (filament 4) | face d'appui sur le plateau | 33 min, 11 g |
| `clips.3mf` | PETG noir (filament 3) | les trois à la fois, sur le flanc, sans support | 21 min, 8,8 g |
| `patron.3mf` | PETG | à plat | 16 min, 7,2 g |

- **Plaquettes** : les trois à la fois, chaque objet a deux pièces, `noir` et `blanc`. Réglages
  imposés par le texte : couches de 0,2 dès la première, lignes de 0,42, Arachne.
- **Visière** : le chant côté plateau entre dans la rainure avec 0,1 mm de jeu par côté : garder
  la compensation de pied d'éléphant du gabarit (0,15).
- **`plaque_bossage`** : dans le creux, le plafond sous la face du connecteur est à 30° de
  l'horizontale : supports en arbre, en kaki, tous dans le creux (x ±11,6, y −22,6 à +4,3 dans le
  repère de la plaque), à retirer par le dos.
- **Clips** : les ailes sont posées du côté de leur oreille : de l'autre, 70 mm² seraient en
  surplomb. Sur le flanc, les parois suivent le profil : la zone qui fléchit (1,4 à 1,8 mm) et le
  bras du crochet (1,6 mm) sont faits de deux parois pleines, et le dessous à coller sort lisse.
- Script d'export des deux plaques : `scripts/export_plaques.py`, puis `uv run plaques_3mf.py`.
- **Snapmaker Orca** écrit le chemin local du fichier dans `source_file` (`Metadata/model_settings.config`)
  à chaque enregistrement : retirer ce champ avant de commiter un 3MF réenregistré, et réinscrire son
  empreinte s'il est verrouillé.

## Support de la carte à borniers

La carte MRD076A avec l'ESP32 est debout, centrée en x = z = 0, antenne en haut, USB-C en bas.
Elle se clipse sans vis sur trois clips, eux-mêmes collés dans des logements du fond
(`scripts/support_carte.py`).

| Élément | Cotes | Paramètres |
| --- | --- | --- |
| Logements | 3, de 1,5 de profond dans le fond de 3, jeu de 0,2 par côté : 88,5 × 12,9 (ailes), 88,5 × 8,4 (milieu) ; z = -44,45 à +44,05 ; x = ±25,7 à ±38,6 et ±4,2 | `clip_log_p`, `clip_log_jeu` |
| Clips | composants `clip_aile` (droite), `clip_aile_miroir` (gauche), `clip_milieu`, dérivés du design source, grand crochet en haut, base à y = 38,5 | `clip_L`, `clip_bas`, `clip_z0`, `clip_aile_l`, `clip_oreille`, `clip_mil_l`, `clip_src_y` |
| Carte | dos du circuit à y = 32,5 (4,5 du fond), butées des ailes à x = ±36,9 | `carte_L`, `carte_W`, `carte_jeu`, `clip_appui` |

Jeux mesurés sur le modèle (`scripts/check_support.py`) : aucune collision ; soudures des
borniers et ailes 0,9 ; ESP32 et témoin 3,74 ; ESP32 et afficheur 5,49 ; borniers et SO-45 7,79 ;
circuit et parois 3,15 ; bouts des clips et parois 1,65 (haut), 1,25 (bas). Fils non modélisés.
Le logement de la carte entre crochets fait 84,7, sa longueur, sans jeu.

Au montage, ne pas coller sous les 10 derniers millimètres du côté du grand crochet : le dessous
du clip y remonte pour laisser le crochet fléchir.

Le câblage passe uniquement par les borniers des côtés. L'ESP32 reste enfiché sur les deux rangées
intérieures ; les deux rangées femelles extérieures restent vides. Entre les clips, il reste 4,5
sous le circuit (2,5 sous les soudures) pour passer des câbles ; pour franchir un clip, 2,7 entre
sa semelle et le circuit.

## Accroche murale

Deux trous de serrure traversent le fond de la coque (`scripts/accroche.py`). Les têtes des vis à
bois de la planche entrent par les grands trous, le boîtier descend, la tige remonte dans la fente
et la tête reste derrière le fond, dans le vide de la coque. Ce sont des coupes droites dans un fond
imprimé contre le plateau : pas de poche, pas de support.

| Élément | Cotes | Paramètres |
| --- | --- | --- |
| Vis, **à mesurer** | tête Ø 8, tige Ø 4 juste sous la tête (valeurs provisoires, paramètres favoris) | `accroche_tete_d`, `accroche_tige_d` |
| Position | axe de la vis, boîtier accroché : x = ±58, à la verticale des SO-45, 116 d'entraxe ; z = 0, à mi-hauteur de la coque | `accroche_x`, `accroche_z` |
| Jeu | 0,3 par côté : grand trou Ø 8,6, fente de 4,6 de large | `accroche_jeu` |
| Course | 10,3, calculée : arrondi de la fente centré à z = -0,3 (le boîtier pend sur sa tige, d'où `accroche_jeu` sous l'axe), grand trou à z = -10,6, la tête recouvre 2 de fond au-delà de lui | `accroche_course`, `accroche_recouvrement` |

Sur la planche : deux vis à la même hauteur, à 116 d'entraxe, le dessous de la tête à 3,4 mm du bois
(fond de 3 + 0,4 de jeu). Boîtier accroché, les vis sont à mi-hauteur : 48 au-dessus et 48 en
dessous. Il faut 10,3 de marge au-dessus pour le poser.

Contrôles (`scripts/check_accroche.py`) : un pavé de 14 de large sur tout le chemin de la tête,
jusqu'à 15 derrière le fond, ne touche rien des deux côtés (corps de l'assemblage ; fils non
modélisés, à tenir hors de ce chemin). Les coupes suivent les paramètres jusqu'à tête 11 / tige 5 et
tête 5 / tige 2,5, y compris quand le centre du grand trou passe au-dessus de z = 0.

La vue `back` des captures MCP sort retournée : pour juger du haut et du bas, imposer la caméra (Z
vers le haut). Dans le bon sens, le grand trou est en bas et la fente monte.

### Patron de perçage

Composant `patron` (`scripts/patron.py`), rangé 5 mm derrière la coque, pour suivre les paramètres
`accroche_*`. Plaque mince aux dimensions de la coque, copie du dos du boîtier : on la plaque sur la
planche et on marque les deux trous.

| Élément | Cotes | Paramètres |
| --- | --- | --- |
| Plaque | 200 × 96 × 0,6 (3 couches) | `patron_ep` |
| Cadre et barre | cadre de 10, barre de 20 centrée sur les trous | `patron_rail`, `patron_barre` |
| Trous | Ø 3, au centre des grands trous des fentes : x = ±58, z = -10,6 | `patron_trou_d`, `patron_z` |
| Repères | encoches de 1,2 × 3 aux quatre milieux | `patron_repere_l`, `patron_repere_p` |

Le contour montre le boîtier au moment où on l'engage : accroché, il finit `accroche_course` plus
bas, soit 10,3. Pour une hauteur finale donnée, poser le patron d'autant plus haut.

`patron_z` suit `accroche_course`, donc la tête de vis : la mesurer avant d'imprimer. Trous du patron
et grands trous de la coque restent confondus avec une tête de 8, 11 et 5.

## Interface des plaques de flanc

`scripts/fenetres_flancs.py`, `plaque_flanc.py`, `plaque_encastree.py`, `plaque_saillie.py`.
`plaque_flanc` est la plaque générique, pleine : **toutes les plaques partent de sa forme** et se
montent sur cette interface. C'est la plaque qui commande : fenêtre, feuillure, inserts et piliers
suivent ses cotes. L'interface est identique sur les deux flancs et symétrique autour de son centre.
Une plaque symétrique va donc des deux côtés ; une plaque asymétrique existe en variantes gauche et
droite.

Chaque plaque est un composant complet : la plaque, ses connecteurs et leur visserie. Toutes les plaques
restent dans le design : on en affiche une par flanc et on masque les autres. Seules les 4 CHC M3×6 du
flanc restent dans `visserie`, puisqu'elles servent à toutes les plaques.

| Élément | Cote | Paramètres |
| --- | --- | --- |
| Plaque | 86 × 32 × 4, coins R 3 : 3 logés dans la feuillure, 1 en saillie du flanc | `plaque_H`, `plaque_P`, `plaque_ep`, `plaque_saillie`, `plaque_R` |
| Centre | y = 21,25, z = 0 : milieu de la partie plate du flanc | `fen_y` |
| Feuillure | plaque + 0,15 de jeu par côté, 3 de profondeur | `plaque_jeu` |
| Bord plat | 2 entre la plaque et l'arrondi, en haut et en bas, calculé depuis `vis_z` | `plaque_bord` |
| Fenêtre | 68 × 24 (y = 9,25 à 33,25), de pilier à pilier | `fen_H`, `fen_P` |
| Vis | 4 CHC M3×6 à 4 des bords : y = 9,25 et 33,25, z = ±39, à la hauteur des vis de platine ; tête à moitié noyée (lamage Ø 6 × 2, elle dépasse de 1), en prise sur les 4 mm de l'insert | `plaque_vis_m`, `flanc_vis_y`, `flanc_vis_z`, `plaque_lamage_d`, `plaque_lamage_p` |
| Logements | au fond de la feuillure : Ø 4,2 × 4,5, puis Ø 3,4 jusqu'à 6 de profondeur | `insert_d`, `insert_p`, `vis_d`, `flanc_vis_p` |
| Appui | 4 côté façade, 9 en haut et en bas, nervure de 2 côté mur | `plaque_appui`, `plaque_appui_z`, `flanc_nervure` |

La partie logée de la plaque (3 mm) est plus épaisse que la paroi (2,5 mm) : côté mur, la feuillure
traverse la paroi, d'où la nervure d'appui. La face intérieure des piliers suit la fenêtre
(`pilier_z`), pour que les inserts soient tout entiers dans les piliers : il reste 2,5 mm de matière
entre un insert Ø 5 et la fenêtre. Les vis de plaque et de platine étant dans le même plan, il reste
1,3 mm entre le fond de leurs perçages, sans effort dessus : les vis s'arrêtent avant. Les perçages de
plaque restent borgnes : plus longue qu'une CHC M3×6, une vis toucherait le fond, puis la FHC M3×12 de
platine, dont la pointe arrive à y = 9. Les FHC M3×12 des plaquettes sortent de 4,2 mm derrière leur
bossage, dans le vide (premier obstacle dans leur axe à plus de 23 mm, sonde
`scripts/check_plaquettes.py`).

Le dépassement ne touche que la plaque : `plaque_saillie` s'ajoute à `plaque_ep` dans son extrusion,
son plan de face et ses perçages. Feuillure, inserts et liaisons restent sur `plaque_ep`, la coque ne
change pas et chaque plaque peut avoir sa valeur. Au-delà de 1 mm, passer aux CHC M3×8. Longueur et
largeur modifient la coque. `plaque_bord` suit `vis_z`, donc l'alignement se maintient si les vis de
platine bougent.

`plaque_flanc` est à plat sur XY, origine au centre de la face d'appui, face visible vers +Z, X dans
la profondeur de la coque, Y en hauteur. À l'impression de la coque, sur le dos, le bord de la fenêtre
côté façade forme un pont de 68 mm (70 environ au tranchage), et celui de la feuillure un pont
d'environ 84 mm.

### Plaque `plaque_bossage`

Bossage incliné : le connecteur regarde 30° vers le haut et l'extérieur (`scripts/plaque_bossage.py`,
sonde `scripts/check_bossage.py`). Composant à part, posé sur le flanc droit par
`jo_plaque_flanc_droite`, à la place de `plaque_flanc:1`, masquée. Le LP-16, ses inserts et ses vis sont
dans le composant ; leurs liaisons sont restées à la racine et les pilotent toujours. Contour, partie logée, dépassement
et vis viennent des paramètres de `plaque_flanc` : la plaque suit l'interface, et les 4 CHC M3×6 de la
plaque générique restent justes. Le LP-16 repose sur le kaki, sa bride fait la finition.

| Élément | Cote | Paramètres |
| --- | --- | --- |
| Rails | 1 de dépassement du flanc, comme la plaque générique | `bossage_rail` (= `plaque_saillie`) |
| Face inclinée | 33 de long, 30° ; pied à z = +10,08, arête à 17,5 du flanc et z = −18,5 | `bossage_face`, `bossage_angle`, `bossage_saillie`, `bossage_crete`, `bossage_haut` |
| Pente | 45°, de l'arête à z = −35, 1 mm après le lamage | `bossage_pied` |
| Creux | largeur de la fenêtre (24), ouvert au dos de z = +5 à −34 ; parois de 6 sous la face, 3 sous la pente, 4 sur les côtés | `bossage_paroi_face`, `bossage_paroi`, `bossage_creux_*` |
| Connecteur | perçage Ø 16,5, 1,5 sous le milieu de la face pour que l'ergot passe le rail (0,5 de jeu) | `bossage_percage`, `bossage_decalage` |
| Inserts | 4 logements Ø 4,2 × 4,5 à 20 d'entraxe, Ø 3,4 jusque dans le creux | `bossage_vis`, `insert_d`, `insert_p`, `vis_d` |

Fixation du LP-16 : d'après le STEP, la bride a un passage Ø 3,2 et une fraisure à 90° de Ø 6, soit du
**M3 à tête fraisée**. Posées dans le modèle : 4 inserts et 4 FHC M3×12 (`insert_connecteur_*`,
`vis_connecteur_*`), la seule FHC M3 du stock. La vis prend les 4 mm de l'insert et sa pointe sort de
2,3 dans le creux, à 4,5 environ de l'arrière du connecteur. Sa tête dépasse de 0,2 de la bride : le
modèle a un bord cylindrique de 0,2 que la fraisure n'a pas (`offset` de −0,2 sur les liaisons). Le
STEP vient de GrabCAD : passage et fraisure à confirmer sur la pièce reçue. Si elle est en M4, il
faudra reprendre les logements et les vis.

Contrôle avec le 2 pôles : aucune interférence entre plaque, connecteur, coque et vis, 0,10 de jeu dans
le perçage, 18,4 du SO-45, 4,6 de la coque, 0,8 entre pointe de vis et coque. Le connecteur se
chevauche lui-même dans son nez (13,4 mm³, sans objet).

`bossage_angle` pilote toute la plaque, connecteur et visserie compris : vérifié à 20° et 45°, perçage
dans l'axe, sans alerte ni interférence. En dessous d'environ 19°, le haut du creux passe de l'autre
côté de l'origine et ses cotes, non signées, ne suivent plus.

La plaque est symétrique en X, un seul composant vaut pour les deux flancs. Mais
`jo_plaque_flanc_gauche` met Y vers le bas : sur le flanc gauche, ajouter 180° autour de Z dans la
liaison, sinon le connecteur regarde vers le bas.

### Plaque `plaque_bossage_fusible`

LP-16 et porte-fusible 5 × 20 sur deux faces en marche, axes parallèles à 45° vers le haut et l'extérieur
(`scripts/plaque_bossage_fusible.py`). Le fusible protège l'arrivée 12 V. Forme « Gorge », retenue après une
étude de sept formes le 05/11/2026 ; document de l'étude : `maquettes/maquette_fusible_gorge`. Composant à
part, posé sur le flanc droit par `jo_plaque_flanc_droite`, avec le LP-16, le porte-fusible, 4 inserts et
4 FHC M3×12 ; leurs liaisons sont dans le composant.

Contour, partie logée, dépassement et vis viennent des paramètres de `plaque_flanc`, lus à la construction.
Les cotes de forme sont en tête du script, pas dans les paramètres du design : pour en changer, supprimer
le composant et relancer le script.

| Élément | Cote |
| --- | --- |
| Face du LP-16 | 34 de long, 45° ; pied haut à 34,4 au-dessus du centre de la plaque ; LP-16 à 18 du pied, soit 1,75 de marge sous la bride, comme sur les côtés |
| Face du fusible | 20 sous celle du LP-16 ; axe à 8,5 de la marche, 1 entre la collerette et le bossage |
| Tube | section en goutte, flancs tangents aux coins du bossage, Ø 22, nez R 8 ; coins du bossage R 4,5, arêtes R 0,5 |
| Gorge | Ø 20, coaxiale au fusible, arrêtée à 2,5 sous la face du LP-16 : traversante, elle mangerait la marge sous la bride |
| Creux | largeur de la fenêtre ; parois de 6 sous la face, 4,5 sous la marche |
| Intérieur du tube | paroi de 4 sous la face, perçage Ø 11,5, empreinte hexagonale de 15,3 sur plats × 3,5 qui bloque l'écrou (on visse par l'extérieur), alésage Ø 18 |

Porte-fusible tourné d'un quart de tour, cosses sur les côtés. Dans le modèle, écrou et rondelles restent où
le STEP les pose, 0,8 sous la paroi : sans effet sur la plaque. Capuchon à X = 128,4, nez du LP-16 à 128,9,
bossage à 124,8.

Contrôle (`controle()`, dans `claudometre`) : seuls les 4 inserts M3 recoupent la plaque, de 92,5 mm³, la
matière qu'ils déplacent à la pose à chaud. Filet (Ø 11 ou M12), écrou et tranchage du tube (paroi de 2,
supports) restent à confirmer sur les pièces. Sur le flanc gauche, ajouter 180° comme pour `plaque_bossage`.

## Cadrans à imprimer

Dans les designs `fond-jauge-*`, les couleurs sont des esquisses DXF, pas des maillages.
`uv run cadran_dxf.py [style] [session|semaine]` écrit `cadran_dxf/` (contours en mm et `cadran.json` :
aire, centre et couleur de chaque morceau), à recopier dans `%TEMP%\claudemetre\cadran_dxf\`.

- Modifier la plaque, les épaisseurs ou les lamages : dans `fond-jauge`, l'enregistrer, puis « Mettre à
  jour » la dérivation dans chaque variante.
- Modifier les graduations ou les textes : dans `so45_print.py`, puis `cadran_dxf.py` et `variante()` de
  `scripts/fond_jauge.py` relancée dans chaque variante (elle remplace les couleurs).
- Nouvelle variante : `derive()` (nouveau design dérivé, à enregistrer) puis `variante()`.

3MF prêts à imprimer, un par cadran, dans `print/` : `fond-jauge-session.3mf` et
`fond-jauge-semaine.3mf`, projets **Snapmaker Orca**, **un objet à 4 pièces, une par couleur** (fond,
echelle, zone, texte), face visible contre le plateau, au centre du plateau. Réglages : gabarit
`u1-4pla-cadrans` de la bibliothèque commune `~/3d/impression-3d`, avec les réglages d'impression du
cadran (`REGLAGES` dans `cadran_3mf.py`). Aucune pièce n'est attribuée à un filament : filaments et têtes
se choisissent au moment d'imprimer. Plus un aperçu de la face (`<variante>_apercu.png`). Ces deux
fichiers sont verrouillés : voir `FICHIERS_VALIDES.md`.

Après toute modification : skill `regenerer-3mf` du projet, ou à la main :

1. `scripts/export_cadrans.py` dans Fusion (copié dans `%TEMP%\claudemetre\`, chargeur de
   `scripts/README.md`) : un STL par composant de chaque variante dans `%TEMP%\claudemetre\export\`. Une
   variante fermée est ouverte en arrière-plan ; une dérivation périmée arrête l'export.
2. `uv run cadran_3mf.py` (ici) : contrôle les maillages (fermés, volumes, couleurs à fleur de face) et
   écrit les 3MF.

Un seul objet, et non 4 : hors projet, Snapmaker Orca croit en pouces tout objet de moins de 9 mm³ (la
zone fait 3,4 mm³) et propose de le mettre à l'échelle. Le fond a des arêtes de contact (zone rouge au bout
de graduations, épaisseur nulle) : sans conséquence à l'impression.
