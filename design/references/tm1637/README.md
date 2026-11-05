# Afficheur TM1637 0,56" : modèle 3D de référence

Module en stock : afficheur 4 chiffres 0,56" à points décimaux (un point entre
chaque chiffre, pas de deux-points), piloté par un TM1637, **segments jaunes**
(AliExpress 1005001970566474).

Source : `Display_4-Didi_LED_TM1637.stp`, téléchargé sur GrabCAD (CATIA V5,
AP214, mm, 2020). Sa description d'origine, en tchèque, dit « Hodinový LED
displej 0.56" TM1637 - zelený » (afficheur d'horloge 0,56", vert). Il diffère de
notre module par sa couleur, que le modèle Fusion et les rendus passent en jaune,
et par son deux-points, absent de notre module.

| Fichier | Contenu |
| --- | --- |
| `Display_4-Didi_LED_TM1637.stp` | modèle STEP complet (PCB, afficheur, TM1637, composants, connecteur) |
| `step_to_segments.py` | extrait les segments du STEP : `uv run step_to_segments.py` |
| `tm1637_segments.json` | contour exact des 28 segments, des 4 points et du deux-points du modèle |

## C'est bien le 0,56"

Le 0,36" mesure environ 30 × 14 mm, avec un PCB de 42 × 24. Ici :

- afficheur de **50,2 × 19,0 × 8,0 mm**, soit la taille standard d'un
  4 chiffres 0,56" ;
- chiffres de **14,7 mm** de haut (0,56" = 14,2 mm), au pas de 12,4 mm,
  inclinés ;
- PCB de **66,0 × 27,2 mm**, la taille relevée sur les modules 0,56" à PCB
  noir.

## Cotes relevées dans le STEP

Origine au centre de la face avant de l'afficheur ; x vers la droite, y vers
le haut, profondeur vers l'arrière.

| Élément | Cote |
| --- | --- |
| Afficheur | 50,2 × 19,0 mm, 8,0 mm de profondeur (face avant à 0) |
| PCB | **66,0 × 27,2 × 1,6 mm**, coins arrondis R 1, de 8,0 à 9,6 mm derrière la face. **Décalé de 1,6 mm vers la droite** par rapport à l'afficheur (x de -31,4 à +34,6) |
| Trous de fixation | 4 × **Ø 3,3 mm** (M3), entraxe **60,0 × 21,5 mm** ; centres à x = -28,4 et +31,6, y = ±10,75 |
| Connecteur | 4 broches au pas de 2,54 (x = +28,4 ; y = -4,32 à +3,30), pastilles aussi à gauche (x = -28,4) |
| Connecteur du modèle | coudé, côté afficheur, broches vers la droite : elles dépassent jusqu'à x = +36,0 |
| TM1637 (SOP-20) | au dos, 13,0 × 10,6 mm, dépasse jusqu'à 12,0 mm derrière la face |
| Encombrement total | 67,4 × 27,2 × 12,0 mm (connecteur coudé compris) |

Dans le boîtier, les SO-45 sont à x = ±58 et leur corps fait Ø 45. Le corps de
droite commence donc vers x = +35,5, juste derrière la platine : le bord droit du
PCB (+34,6) n'en est qu'à **0,9 mm** ; à gauche, il reste 4,1 mm. Le connecteur du
modèle le toucherait : il est retiré du modèle Fusion. Sur l'objet, pin header coudé
tourné vers l'intérieur de l'afficheur.
