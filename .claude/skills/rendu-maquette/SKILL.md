---
name: rendu-maquette
description: "Refait les rendus Blender de la maquette `jj_fusion` du claudomètre (images, vidéo du voyant) depuis le design Fusion `claudometre`, et republie la galerie. À utiliser quand on demande de nouveaux rendus, une nouvelle vue, la vidéo, ou de mettre à jour la galerie après un changement du design. Pas pour la page 3D interactive (skill regenerer-maquette)."
---

# Rendus `jj_fusion`

```
claudometre (Fusion)
   │ scripts/export_blender.py, run()         lecture seule, corps visibles seulement
   ▼
design/fusion/blender/claudometre.{bin,json}  suivi par Git
   │ design/blender/render.sh, anim.sh        Blender Windows, depuis WSL
   ▼
design/renders/<variante>.png, .mp4
   │ JPEG de 1500 px
   ▼
design/gallery/img/ ──► artefact de la galerie (lien dans ARTEFACTS.md)
```

Décor, matériaux et ajouts absents de Fusion : `docs/maquettes.md`.

## 1. Préparer le design

Charger le skill `fusion360`. `run` n'exporte que ce qui est visible : **la plaque affichée dans Fusion est celle du
rendu**. Vérifier avec l'utilisateur laquelle il veut voir, et lui demander d'enregistrer.

`jj_fusion_detail` cadre `plaque_bossage` et sa fiche. Avec une autre plaque, revoir ce cadrage. La fiche suit la pose
du LP-16 visible : vérifier son câble sur une plaque à un autre angle.

## 2. Exporter

```bash
. ./prive.env
cp design/fusion/scripts/export_blender.py "$WIN_TEMP/claudemetre/"
```

Chargeur de `fusion_mcp_execute` (script, `readOnly: true`), qui appelle `ns['run'](ctx)` : voir l'étape 2 du skill
`regenerer-maquette`. Puis :

```bash
cp "$WIN_TEMP/claudemetre/export/blender/claudometre."* design/fusion/blender/
```

Sans nouvel export, le rendu montre le design de la version enregistrée dans `claudometre.json`.

## 3. Rendre

Toujours un brouillon d'abord : le rendu final tourne sur le processeur.

```bash
design/blender/render.sh jj_fusion preview
design/blender/render.sh jj_fusion final
```

| Variante | Vue |
| --- | --- |
| `jj_fusion` | d'ensemble, côté connecteur, câble entier |
| `jj_fusion_face` | de face, cadrans lisibles |
| `jj_fusion_detail` | gros plan de la plaque et de la fiche |
| `jj_fusion_soir` | de face, lumière du soir |

Les brouillons vont dans `design/renders/preview/`. Les lire avant de lancer le final : aiguilles, plaque, fiche et
câble à leur place. Les valeurs affichées sont dans `variants6.py` (`SESSION`, `SEMAINE`, `RESET`).

Vidéo du voyant, en quelques minutes (3 images rendues, les autres calculées) :

```bash
design/blender/anim.sh jj_fusion_soir final
```

## 4. Galerie

Source : `design/gallery/jj_fusion.html`, images dans `design/gallery/img/`, en JPEG de 1500 px de large pour les
images, et la vidéo telle quelle. Reprendre le titre si la version du design y figure.

L'URL est dans `ARTEFACTS.md` : lire l'artefact (`action: read`, avec seulement `url`), puis le republier sur cette
URL, avec les images dans `files`.

## 5. Finir

- `docs/maquettes.md` : mettre à jour la version du design et ce qui a changé, puis skill `regenerer-docs-en`.
- Ne commiter et ne pousser que sur demande.
