# Connecteurs CNLINKO LP-16 : modèles 3D de référence

Embases LP-16 à bride carrée, pour les plaques de flanc de la coque. Le 2 pôles
est posé sur `plaque_bossage` ; l'USB-C n'est pas utilisé. Ces modèles servent à
Fusion.

Source : deux archives GrabCAD, `cnlinko-connector-lp16-2-pole-1.snapshot.12.zip`
et `cnlinko-connector-lp16-usbc-1.snapshot.5.zip`. Exports Shapr3D, en mm, copiés
tels quels. Rien n'indique qu'ils viennent du fabricant : cotes à confirmer sur la
pièce reçue.

| Fichier | Contenu |
| --- | --- |
| `LP-16-2pole.step` (`.iges`) | embase 2 pôles, 12 solides |
| `LP16-USBC.step` (`.iges`) | embase USB-C, 5 solides |

Dans le 2 pôles, 7 des 12 solides sont sans volume : de petits éléments sur la
pente de l'ergot (y ≈ 15), sans doute le marquage. Ils sont à écarter dans
Fusion.

## Repère

Le même pour les deux modèles : Z est l'axe du connecteur, l'origine est au
centre de la face arrière de la bride (celle qui porte sur le panneau), +Z va
vers la fiche et +Y vers l'ergot.

## Cotes

Mesurées sur les STEP, comparées au plan coté LP-16 de la fiche Amazon.

| Cote | Plan | 2 pôles | USB-C |
| --- | --- | --- | --- |
| Bride | 28,5 × 28,5 | 28,5 × 28,5 | 28,5 × 28,5 |
| Hauteur avec l'ergot | 31,5 | 31,75 | 31,75 |
| Fixation | 4 × Ø 3,2 à 20 d'entraxe | identique, fraisure 90° Ø 6 | identique |
| Perçage du panneau | Ø 16,5 | fût Ø 16,3 | fût Ø 16,3 |
| Devant la face d'appui | 11,8 | 12 | 12 |
| Fût Ø 16,3 derrière la face d'appui | 10 | 10 | 10 |
| Profondeur totale derrière la face d'appui | non coté | **15** | **17,7** |
| Longueur totale | 21,8 | 27 | 29,7 |

Communes aux deux : bride de 3,5 d'épaisseur, angles R 4,25, nez Ø 19,5.

## Pour les plaques de flanc

- **Le plan ne cote que le fût.** Le noyau central dépasse derrière lui : une
  cloison et deux cosses à souder Ø 2,5 à 5,5 d'entraxe sur le 2 pôles (cosses
  jusqu'à z = −14, cloison jusqu'à −15), un noyau Ø 11 sur l'USB-C.
- **L'USB-C est femelle des deux côtés.** La cavité arrière mesure 8,3 × 2,5
  sur 5,2 de profondeur, avec sa languette : à l'intérieur de la coque, il faut
  y brancher une fiche USB-C.
- **Sur la plaque `plaque_bossage`** (connecteur 30° vers le haut,
  `design/fusion/README.md`) : le 2 pôles reste à 18,4 mm du SO-45, fils et fiche
  non comptés. Il se fixe en M3 à tête fraisée (FHC M3×12) : à confirmer sur la
  pièce reçue.

## Dans Fusion

Les deux modèles sont dans `claudometre/models/` :
`connecteur_LP-16_2poles` (les 7 solides du marquage retirés) et
`connecteur_LP-16_USB-C`. Le 2 pôles est posé sur
`plaque_bossage`, peint en noir corps par corps dans `claudometre` : le STEP
porte ses couleurs (bride gris clair), qui passent avant celle de l'occurrence.
