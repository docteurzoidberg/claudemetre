# Voltmètre SO-45 : modèle 3D de référence

Source : modèle `so-45-voltmeter` téléchargé sur GrabCAD
(`so-45-voltmeter-1.snapshot.1.zip`, novembre 2025).

| Fichier | Contenu |
| --- | --- |
| `so-45-voltmeter.step` | modèle STEP (AP214, unités mm), à importer dans Fusion, FreeCAD, KiCad… |
| `so-45-voltmeter.f3d` | modèle Fusion 360 d'origine |
| `so-45-voltmeter-front/side/back.png` | aperçus fournis avec le modèle |

Le modèle ne décrit que le boîtier : il n'y a pas le cadran, l'aiguille ni le
mécanisme.

## Cotes relevées dans le STEP

Axe de profondeur : la face de la collerette côté corps est à 0, l'avant est
positif.

| Élément | Cote |
| --- | --- |
| Collerette de fixation | **carrée 46,8 × 46,8 mm**, épaisseur **4,65 mm** (de 0 à +4,65) |
| Trous de fixation | 4 × **Ø 4,0 mm**, entraxe **37 × 37 mm** (centres à ±18,5) |
| Lunette avant | **Ø 45 mm**, dépasse de **4,65 mm** devant la collerette (de +4,65 à +9,3) |
| Fenêtre | **Ø 38,8 mm**, en **« D »** : le bas est masqué par un segment noir dont la corde passe à 12,65 mm du centre (l'axe de l'aiguille est caché derrière) |
| Corps arrière | **Ø 45 mm**, **24,4 mm** de long derrière la collerette |
| Bornes | 2 tiges filetées **M4**, longueur **8,5 mm**, entraxe **18 mm**, décalées de 12,5 mm par rapport à l'axe, **du côté opposé au segment noir du « D »** : vers le haut quand le cadran est à l'endroit |
| Encombrement total | 46,8 × 46,8 × **42,2 mm** (bornes comprises) ; 33,7 mm sans les bornes |

```
          vue de côté (avant à droite)
                  ┌──┐
    bornes M4     │  │← collerette 46,8 carrée, ép. 4,65
   ═══╗ ┌─────────┤  ├──┐
      ║ │  corps  │  │  │← lunette Ø45, saillie 4,65
   ═══╝ │  Ø 45   │  │  │
        └─────────┤  ├──┘
          24,4    └──┘
   ←8,5→
```

## Cadran d'origine (mesuré sur la vraie pièce)

Plaque d'alu blanche démontée et photographiée à plat sur un fond imprimé
(41 × 51 mm au plan) avec un réglet. La photo
(`cadran_photo.jpg`) a été redressée par calcul : la plaque doit être ronde,
les traits du réglet réguliers et les bords du fond parallèles. Contrôle
indépendant : le fond redressé mesure 50,9 mm de large pour 51 au plan. Le
bord de la plaque est rond à 0,02 mm près. Les graduations d'origine sont
régulières à 0,04 mm près. Vue redressée, modèle superposé en rouge :
`cadran_redresse.jpg`. Précision estimée : ±0,1 mm. Le flanc gauche de la
découpe, noyé dans un reflet, est repris du côté droit par symétrie.

Repère : origine au centre de la plaque, x à droite, y vers le haut.

| Élément | Cote |
| --- | --- |
| Plaque | disque **Ø 40,8** sur photo ; cadran imprimé **Ø 40,4**, pour entrer sans forcer |
| Découpe centrale (équipage mobile) | **dôme** de R 8,76 centré à y = −8,2 (sommet à +0,56) ; **épaulements** à y = −5,22, raccordés par des congés de R 3,53 à des **flancs verticaux** à x = ±12,31 qui descendent jusqu'au bord (pointes à y = −16,27) |
| Trous de vis (fixation du cadran) | 2 × **Ø 2,6** à x = **±15,51**, y = −2,3 (entraxe **31,02**), bord embouti ; la plaque repose sur **deux piliers cylindriques Ø 5** |
| **Axe de l'aiguille** | x = 0, **y = −8,95** (centre de l'arc de l'échelle, où convergent les traits) |
| Échelle d'origine | 0-5 V, 26 traits tous les 0,2 V ; ligne de base de R 18,54 à 18,95 depuis l'axe ; petits traits jusqu'à R 20,4 |
| **Débattement** 0 → pleine échelle | **76,8°** (trait 0 à −39,1°, trait 5 V à +37,8° de la verticale) |

Photo de face du voltmètre monté : `voltmetre_face.jpg`. Relevés faits en
calant la photo sur les vis et les traits 0 et 5 (±0,5 mm) :

| Élément | Cote |
| --- | --- |
| Centre de la bague laiton de l'équipage | (−0,6 ; −8,8) : confirme l'axe mesuré sur le cadran |
| **Aiguille** | noire, pointe rouge, **≈ 22,5 mm** depuis l'axe : la pointe arrive au bout des grands traits |
| **Bord du masque** (corde de la fenêtre en « D ») | **y ≈ −11,6** (le modèle GrabCAD dit −12,65) |
| Réglage du zéro | vis noire à fente sur la façade, sous la fenêtre : accessible de face |
| Vis du cadran | têtes cruciformes, visibles dans la fenêtre |

L'axe (−8,95) est au-dessus du bord du masque : la découpe et l'équipage
mobile (bague laiton, fils, étrier) restent visibles dans la fenêtre. Les cotes sont reprises dans
`design/dials/dial_so45_spec.json` (bloc `plate`, `pivot_z`, `sweep_deg`). Le
design Fusion `fond-jauge` montre la plaque sur la photo
(`design/fusion/scripts/fond_jauge.py`).

## Électrique

Résistance série d'origine `R_s` (calibre 0-5 V) : **4,65 kΩ**. Les deux voltmètres sont
marqués : **A = session**, **B = semaine**.

| Élément | A (session) | B (semaine) |
| --- | --- | --- |
| `R_tot` entre les bornes, d'origine | **4,77 kΩ** | **4,81 kΩ** |
| Cadre mobile `R_g` = `R_tot` − `R_s` | ≈ 120 Ω | ≈ 160 Ω |
| Courant de pleine échelle (5 V / `R_tot`) | ≈ 1,05 mA | ≈ 1,04 mA (galvanomètre de 1 mA) |
| Avec 6,2 kΩ en parallèle : tension du 100 % imprimé | ≈ 2,93 V (89 % de rapport cyclique) | ≈ 2,95 V (89 %) |
| Avec 6,2 kΩ en parallèle : résistance entre les bornes | ≈ 2,78 kΩ | ≈ 2,82 kΩ |

**6,2 kΩ en parallèle sur `R_s` seule**, soudée sur les deux, ramène la pleine échelle vers 3 V :
rien à dessouder, c'est réversible, et une marge de calibration reste disponible. Le réglage
d'usine n'est pas exact : la calibration logicielle de chaque jauge corrige l'écart.

### Marge de calibration

L'ESP doit pouvoir déplacer chaque aiguille un peu au-delà des traits imprimés, aux deux bouts de
l'échelle.

**En haut, marge électrique** : ce que le GPIO (3,3 V) donne au-delà de la tension du 100 % imprimé,
≈ 12 % en nominal, ≈ 5 % au pire (rail 3,3 V de la carte à −2 %, 50 mV perdus dans la sortie GPIO à
1 mA, résistance ajoutée à +5 %, galvanomètre à +1 %). Le 100 % imprimé est 0,6° après le trait 5 V
d'origine, soit 0,8 % de courant en plus. La résolution reste large : en PWM 10 bits, le 100 % tombe
vers le pas 910.

**En bas, marge mécanique** : le PWM ne descend pas sous zéro. La vis du zéro (en façade) met
l'aiguille au repos un peu sous le 0 % imprimé ; le 0 % logiciel est alors un petit rapport cyclique.
Le cadran imprimé y aide : son échelle est centrée (±38,4°), donc son 0 % est 0,7° au-dessus du trait
0 d'origine (−39,1°).

## Montage dans le boîtier

Collerette **devant** la platine : passage Ø 46 pour le corps, la collerette carrée et ses 4 vis
restent visibles. Profondeur derrière la collerette : 24,4 mm + 8,5 mm de bornes, plus les cosses.
