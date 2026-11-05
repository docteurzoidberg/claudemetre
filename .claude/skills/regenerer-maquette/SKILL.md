---
name: regenerer-maquette
description: "Régénère la maquette 3D interactive du claudomètre (maquette/claudometre.glb, page three.js assemblé / éclaté) depuis le design Fusion `claudometre`, la contrôle et republie l'artefact « Claudemètre éclaté ». À utiliser quand le design a changé et qu'on s'apprête à pousser, après une modification de maquette/ (pièce, plaque, texte de fiche), ou quand on demande de mettre à jour la maquette ou sa page. Pas pour les rendus Blender `jj_fusion` (skill rendu-maquette)."
---

# Maquette 3D

```
claudometre (Fusion)
   │ scripts/export_blender.py, complet()   lecture seule
   ▼
design/fusion/web/claudometre.{bin,json}    hors dépôt ; extras.* viennent de Blender
   │ uv run pack.py                         dans maquette/
   ▼
maquette/claudometre.glb ──► GitHub Pages, au push
   │ page_autonome.py                       dans ce skill
   ▼
eclate.html ──► artefact « Claudemètre éclaté » (lien dans ARTEFACTS.md)
```

Réglages de `pack.py` et de la page : `maquette/README.md`. Une modification de `main.js`, `index.html` ou
`style.css` seule ne demande pas de repasser par Fusion : aller à l'étape 4.

## 1. Faut-il régénérer ?

Version du design dans le modèle :

```bash
python3 -c "import json,struct;f=open('maquette/claudometre.glb','rb');f.seek(12);n,=struct.unpack('<I',f.read(4));f.seek(20);print(json.loads(f.read(n))['asset']['extras']['version'])"
```

À comparer à `dataFile.versionNumber` de `claudometre`, par une sonde en lecture seule. Si `isModified` est vrai,
demander à l'utilisateur d'enregistrer : l'export prend l'état ouvert, mais le GLB porterait la version précédente.

## 2. Exporter depuis Fusion

Charger le skill `fusion360`. `claudometre` doit être le document actif : l'export s'arrête sinon.

```bash
. ./prive.env
cp design/fusion/scripts/export_blender.py "$WIN_TEMP/claudemetre/"
```

Puis `fusion_mcp_execute` (script, `readOnly: true`) :

```python
import os
def run(ctx):
    p = os.path.join(os.environ['TEMP'], 'claudemetre', 'export_blender.py')
    ns = {'__file__': p}
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), ns)
    ns['complet'](ctx)
```

`complet` exporte aussi les plaques masquées. Le résumé donne la version et le nombre de corps (v30 : 1351). Une
ligne « écart 5,5 mm » sur le LP-16 est un faux positif des boîtes Fusion : le maillage est juste. Puis :

```bash
cp "$WIN_TEMP/claudemetre/export/web/claudometre."* design/fusion/web/
```

Si les ajouts de Blender ont changé (aiguilles, vitres, fiche, câble), refaire aussi `extras.*` : étape 2 de
`maquette/README.md`.

## 3. Faire le modèle

```bash
cd maquette && uv run pack.py
```

v30 : 7,0 Mo, 38 pièces, 65 maillages, 320 382 triangles. Une pièce ajoutée au design fait échouer le script tant
qu'elle n'est pas rangée dans `classe()`. Une nouvelle plaque : skill `nouvelle-plaque`.

## 4. Faire et contrôler la page

`W` : un dossier du scratchpad. Chromium est un snap : ses captures vont dans le home, pas dans `/tmp`.

```bash
python3 .claude/skills/regenerer-maquette/page_autonome.py "$W"
(nohup python3 .claude/skills/regenerer-maquette/serve_csp.py "$W" >/dev/null 2>&1 &)
mkdir -p ~/cm-shot-tmp
capture() {  # nom, paramètres de la page, taille de fenêtre
  timeout 100 chromium-browser --headless=new --no-sandbox --use-angle=swiftshader --use-gl=angle \
    --enable-unsafe-swiftshader --hide-scrollbars --user-data-dir=$HOME/cm-shot-tmp/p$1 --window-size=${3:-1500,1000} \
    --virtual-time-budget=40000 --enable-logging=stderr --v=0 --screenshot=$HOME/cm-shot-tmp/$1.png \
    "http://127.0.0.1:8931/test.html?$2" 2>&1 | grep -E "CONSOLE|Refused|Error|error:" \
    | grep -vE "dbus|gpu_|vaapi|ALSA|gcm|fontconfig|Vulkan"
}
capture fusible "plaque=fusible"
capture lp16 "plaque=lp16&ouverture=60&vue=face"
capture pleine "plaque=pleine&vue=dos"
capture telephone "plaque=lp16" 390,1560
```

La console doit rester vide. Lire chaque capture : modèle présent, liste des pièces adaptée à la plaque, câble droit,
pas de débordement sur téléphone. Toute plaque ajoutée a sa capture.

Ensuite, déplacer les captures dans le scratchpad et nettoyer. `pkill -f` tuerait le shell lui-même :

```bash
fuser -k 8931/tcp
rm -rf ~/cm-shot-tmp
```

## 5. Publier

L'URL est dans `ARTEFACTS.md`, ligne « Claudemètre éclaté » : elle ne va jamais dans un fichier suivi par Git.

1. `Artifact`, `action: read`, avec seulement `url` : une publication sur un artefact d'un autre échange est refusée
   sans cette lecture.
2. `Artifact`, `action: publish`, avec `url` et `file_path` sur `$W/eclate.html`, sans `icon`.

La page locale ne prouve pas tout : demander à l'utilisateur d'y jeter un œil sur claude.ai.

## 6. Finir

Ne commiter et ne pousser que sur demande. `maquette/` part sur GitHub Pages au push : le GLB est commité, l'action
ne régénère rien.
