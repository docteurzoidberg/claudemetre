# Maquette 3D

Page statique pour voir le Claudemètre assemblé ou éclaté : `index.html`, `main.js`, `style.css` et le
modèle `claudometre.glb`. Pas de npm ni de build : three.js vient de jsDelivr (version fixée dans
l'importmap de `index.html`).

L'action `.github/workflows/pages.yml` publie ce dossier sur GitHub Pages à chaque push sur `main` qui le
touche. Elle ne régénère rien : le GLB est commité, parce qu'il dépend de Fusion. Il faut régler une fois
la source de Pages sur « GitHub Actions » dans les réglages du dépôt.

## Mettre à jour avant de pousser

À faire **juste avant de pousser sur la remote**, si le design a changé. Inutile pendant le développement.

1. **Fusion** : ouvrir `claudometre`, copier `design/fusion/scripts/export_blender.py` dans
   `%TEMP%\claudemetre\` et lancer sa fonction `complet` (lecture seule, voir
   `design/fusion/scripts/README.md`). Copier `%TEMP%\claudemetre\export\web\claudometre.*` dans
   `design/fusion/web/` (hors dépôt).
2. **Blender**, seulement si les ajouts de la maquette ont changé (aiguilles, vitres, fiche, câble) :

   ```sh
   blender.exe -b design/blender/scenes/jj_fusion.blend -P design/blender/export_web.py -- <dossier>
   ```

   puis copier `extras.bin` et `extras.json` dans `design/fusion/web/`. `blender.exe` tourne sous Windows :
   chemins à passer par `wslpath -w`.
3. **Modèle** : `cd maquette && uv run pack.py`. Une pièce ajoutée au design fait échouer le script tant
   qu'elle n'est pas rangée dans `classe()`.
4. **Contrôle** : `python3 -m http.server -d maquette 8000`, puis http://localhost:8000.
5. Commiter `maquette/` et pousser : l'action publie.

## Ce que règle `pack.py`

- `PIECES` : déplacement de chaque pièce à l'éclaté, en mm dans le repère de Fusion, et son groupe dans la
  liste de la page. La coque ne bouge pas. Les textes des fiches sont dans `GROUPES`, en tête de `main.js`.
- `MATERIAUX` : couleur, rugosité et métal. La carte n'a qu'une couleur dans Fusion : `carte()` lui rend
  celles de sa photo (`design/references/mrd076a/`).
- `segments()` : l'heure affichée, 14:32 comme sur les rendus.

`?ouverture=40&vue=face` dans l'adresse ouvre la page à 40 %, de face, sans l'animation du début.
