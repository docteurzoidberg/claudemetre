# Témoin CLAUDE du claudomètre

Le témoin CLAUDE (légende éclairée par un tronçon de WS2812B) est un **témoin
encastrable** produit par un outil générique, développé à part :
**`~/3d/generateur-temoin-lumineux`** (commande `temoin`, pilotée par le skill
`temoin-lumineux`). L'outil fait le témoin ; le claudomètre garde ce qui lui est
propre.

| Générateur (générique) | Claudomètre |
| --- | --- |
| cadre, légende, boîte à lumière, fond, vis et inserts | preset `design/temoin/claude.json` |
| 3MF multi-filament, STL, STEP ; nomenclature et cotes de découpe dans son résumé | découpe de la platine, position dans l'assemblage |
| contrôles (traits de la légende, fixation, LED) | états et couleurs dans le firmware et la carte Lovelace |

La platine ne porte qu'une découpe rectangulaire et 2 trous Ø 3,4 : changer la
légende, c'est 2 vis et une petite pièce à réimprimer.

## Utilisation

On demande « génère le témoin du claudemètre », ou on modifie le preset pour le
refaire. Le skill `temoin-lumineux` lit `design/temoin/claude.json`, lance les
contrôles puis la génération, et écrit les fichiers dans `design/temoin/export/`
(régénérables, jamais retouchés à la main). Ensuite, avec le skill `fusion360`, on
met à jour le design `claude` inséré dans `claudometre`, et la découpe de la platine
suit les cotes du résumé.

## Preset CLAUDE

| Réglage | Valeur | Remarque |
| --- | --- | --- |
| Légende | `CLAUDE`, Barlow Condensed SemiBold, lettres lumineuses, fond `#111111` | même police que les cadrans ; capitales de 6,64 mm (calculées) |
| Fenêtre | 32 × 11 mm | |
| Cadre | 52 × 18 mm, `#4b5320` | sans visière |
| Panneau | 3 mm (`platine_ep`) | |
| Fixation | 2 FHC M3×8 (ISO 10642) noires + 2 inserts à chaud M3 (perçage Ø 4 × 5,5), entraxe 42 | le générateur annonce M3×10 ; M3×8 prises sur un reste de stock |
| Éclairage | ruban WS2812B 5 V à 144 LED/m, 4 LED, fils à gauche vus de face | `led_count: 4` dans le firmware ; le générateur annonce 5 LED |
| Filaments | tout en PETG : cadre kaki, boîte et fond noirs, masque noir, lettres et voile transparents | comme le reste du boîtier |
| États | `claude_actif` ambre en respiration, `claude_needattention` rouge clignotant, prioritaire | |

Cotes dérivées : découpe 34,8 × 13,8 mm, 2 trous Ø 3,4 à 42 d'entraxe, centrés sur
la fenêtre. Le cadre déborde la découpe de 8,6 mm à gauche et à droite, de 2,1 mm en
haut et en bas, et il reste 1,9 mm de platine entre la découpe et chaque trou de vis.

Contrôles du générateur : deux avertissements sans gêne à l'impression, un espace
du masque plus fin que la buse (0,05 mm² en x = −2,9) et les LED extrêmes à 0,39 mm
derrière le cadre, hors de la fenêtre.

## Sur l'objet

- Position : x = 0, z = −26, sous RÉINIT., à 2,5 mm de cette plaquette. Bords du
  cadre à x = ±26, à 12 mm des plaquettes SESSION / SEMAINE.
- Signal en 3,3 V : le tronçon est alimenté à travers une diode 1N400x, qui descend
  son seuil haut sous 3,3 V, sans level shifter.
- Fils soudés sur le ruban, férules côté carte à borniers.
