# Maquette

La maquette à jour est `jj_fusion` : la géométrie vient de l'assemblage Fusion `claudometre`
(version 28), corps par corps. Décor, lumière et matériaux sont dans `cm_lib.py`, avec le sens
d'impression réel de chaque pièce.

Rendus : `design/renders/<variante>.png` ; scènes Blender :
`design/blender/scenes/<variante>.blend` ; régénérer avec
`design/blender/render.sh <variante> final`. Valeurs affichées : session 62 %, semaine 38 %,
reset à 14:32.

## Version actuelle

| Élément | Choix |
| --- | --- |
| Boîtier | coque kaki, platine noire, façade droite, visière au-dessus de l'afficheur |
| Jauges | deux SO-45, collerette devant la platine : carré et vis visibles |
| Cadrans | style sombre ; ils ne portent que l'unité, en haut : « % · 5 H » ou « % · 7 J » |
| Afficheur | TM1637 0,56", segments jaunes |
| Plaquettes | SESSION, SEMAINE et RÉINIT., vissées : le nom de l'instrument est ici, pas sur le cadran |
| Voyant | légende CLAUDE éclairée, témoin encastrable sans visière, centré sur la rangée des plaquettes SESSION / SEMAINE |
| Flancs | une fenêtre par flanc, fermée par une plaque amovible : changer de connecteur, c'est refaire la plaque, pas la coque. À droite `plaque_bossage`, connecteur LP-16 à 30° vers le haut ; à gauche `plaque_flanc`, pleine |

Cotes et interfaces : `design/fusion/README.md`. Témoin : [temoin.md](temoin.md).

## Vues et mise à jour

| Rendu | Vue |
| --- | --- |
| `jj_fusion` | d'ensemble, côté connecteur, câble entier |
| `jj_fusion_face` | de face, cadrans lisibles |
| `jj_fusion_detail` | gros plan de `plaque_bossage` et de la fiche |
| `jj_fusion_soir` | de face, lumière du soir ; aussi en vidéo (`jj_fusion_soir.mp4`) |

- **Pour mettre à jour** : `design/fusion/scripts/export_blender.py` dans Fusion, copier
  `%TEMP%\claudemetre\export\blender\claudometre.*` dans `design/fusion/blender/`, puis
  `design/blender/render.sh <variante> final`. L'export ne modifie pas le design.
- **Page de la maquette** (artefact privé, voir `ARTEFACTS.md`) : source
  `design/gallery/jj_fusion.html`, images dans `design/gallery/img/`. Pour ajouter une vue : la
  rendre, la convertir en JPEG 1500 px dans `design/gallery/img/`, puis republier sur la même URL.
- **Ajouté dans `variants6.py`, absent de Fusion** : aiguilles, équipage mobile (moyeu laiton,
  étriers), vitres et vis du zéro des SO-45, fiche LP-16 et câble Ø 5, 2 FHC du
  cadre du témoin. Rien de ceci n'est coté : c'est de l'illustration, d'après
  `design/references/so45/voltmetre_face.jpg`.
- **Aiguilles** : noires à pointe rouge, comme les vraies (`SESSION`, `SEMAINE` et `RESET` de
  `variants6.py`). Sur le cadran sombre, seule la pointe se voit bien.
- **Embase LP-16** : noire, comme la vraie, pas gris clair comme le STEP.
- **Laissés de côté, invisibles boîtier fermé** : carte, clips, inserts, arrière de l'afficheur.
- **Voyant animé** : images clés dans la scène, au rythme du firmware (`esphome/temoin.yaml`) :
  2 respirations ambre de 3,2 s, 100 % → 35 % → 100 %, puis 3 clignotements rouges de 1 s, soit
  235 images à 25 images/s (`SEQUENCE` dans `variants6.py`). La scène se joue dans Blender.
- **Vidéo** : `design/blender/anim.sh <variante> final`. Cycles tourne sur le processeur (pas de
  GPU sur ce poste) : `anim.py` ne rend que 3 images, voyant éteint, ambre et rouge à 100 %, et
  calcule les autres en linéaire (la lumière s'additionne). Même résultat qu'image par image, sans
  scintillement de bruit, en quelques minutes.

## Page 3D assemblé / éclaté (`maquette/`)

Le modèle avec toutes les pièces internes (carte, clips, inserts, visserie), dans une page
three.js à manipuler : choix de la plaque et de ses connecteurs (pleine, LP-16, LP-16 et fusible), ouverture de
l'éclaté, quatre vues, voyant au rythme du firmware, pièces à masquer, fiche de chaque pièce au survol. Publiée sur GitHub Pages par une action, et à mettre à jour juste avant de
pousser : procédure dans `maquette/README.md`.
