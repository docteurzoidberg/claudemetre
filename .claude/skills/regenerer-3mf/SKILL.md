---
name: regenerer-3mf
description: "Régénère les 3MF prêts à imprimer du claudomètre dans design/fusion/print/ depuis les designs Fusion : coque, platine, visière, plaquettes, plaques de flanc, clips, patron de perçage et cadrans (fond-jauge-session, fond-jauge-semaine). À utiliser après une modification d'une de ces pièces, de ses réglages d'impression, de fond-jauge, d'une variante, ou des graduations et textes des cadrans (so45_print.py, dial_so45_spec.json), ou quand on demande un 3MF."
---

# 3MF à imprimer

**Cadrans :** procédure à part, dans `cadrans.md` à côté de ce fichier. Les lignes ci-dessous valent pour le reste.

```
claudometre (Fusion, document actif)
   │ scripts/export_<pièce>.py, run()
   ▼
%TEMP%\claudemetre\export\…   STL et json : volumes, cotes, version
   │ uv run <pièce>_3mf.py     WSL, dans design/fusion
   ▼
design/fusion/print/<pièce>.3mf
```

| Pièce | Export | Générateur | Sortie |
| --- | --- | --- | --- |
| Coque | `export_coque.py` | `coque_3mf.py` | `coque.3mf` |
| Platine | `export_platine.py` | `platine_3mf.py` | `platine.3mf` |
| Visière | `export_visiere.py` | `visiere_3mf.py` | `visiere.3mf` |
| Plaquettes | `export_plaquettes.py` | `plaquettes_3mf.py` | `plaquettes.3mf` |
| Plaques de flanc | `export_plaques.py` | `plaques_3mf.py` | `plaque_flanc.3mf`, `plaque_bossage.3mf` |
| Clips | `export_clips.py` | `clips_3mf.py` | `clips.3mf` |
| Patron | `export_patron.py` | `patron_3mf.py` | `patron.3mf` |

Matière, position et temps de chaque pièce : `design/fusion/README.md`, section « Fichiers à imprimer ». Réglages :
en tête de chaque générateur. Une plaque absente de `KEYS` et de `PLAQUES` n'est pas exportée : skill
`nouvelle-plaque`.

**Avant de commencer :**
- **Platine :** déjà imprimée, elle ne doit plus changer (`CLAUDE.md`). Ne la régénérer que si l'utilisateur le demande.
- **Patron :** ses trous suivent `accroche_*`, à mesurer sur les vis avant d'imprimer.

## 1. Exporter depuis Fusion

Charger le skill `fusion360`, et `impression-3d` pour la suite. `claudometre` doit être le document actif. Demander à
l'utilisateur d'enregistrer : l'export prend l'état ouvert, mais le signale.

```bash
. ./prive.env
cp design/fusion/scripts/export_<pièce>.py "$WIN_TEMP/claudemetre/"
```

Puis `fusion_mcp_execute` (script) :

```python
import os
def run(ctx):
    p = os.path.join(os.environ['TEMP'], 'claudemetre', 'export_<pièce>.py')
    ns = {'__file__': p}
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), ns)
    ns['run'](ctx)
```

L'export s'arrête sur une fonction en erreur dans la timeline : à corriger dans Fusion.

## 2. Écrire le 3MF

```bash
cd design/fusion && uv run <pièce>_3mf.py
```

Le générateur lit l'export dans le Temp Windows et contrôle : maillage fermé, volume égal à celui du corps Fusion,
cotes. Il s'arrête au premier écart : en chercher la cause, ne pas assouplir le contrôle.

**Fichiers verrouillés** (`design/fusion/FICHIERS_VALIDES.md`) : les générateurs ne les réécrivent pas et mettent la
nouvelle version à part. Pour la livrer : la montrer à l'utilisateur, et seulement à sa demande `imp3d valides
retirer`, régénérer, puis `imp3d valides ajouter`.

## 3. Vérifier

```bash
cd design/fusion && imp3d tranche print/<pièce>.3mf --garder
```

Comparer temps et masse à la table de `design/fusion/README.md`, et l'y mettre à jour s'ils changent.

Donner à l'utilisateur le chemin Windows : `WSL_PROJET` de `prive.env`, suivi de `\design\fusion\print\`.

## 4. Finir

Si l'utilisateur réenregistre un 3MF dans Snapmaker Orca, le logiciel y écrit le chemin local (`source_file`, dans
`Metadata/model_settings.config`). Le hook `pre-commit` ne lit pas les binaires : retirer ce champ avant de commiter,
et réinscrire l'empreinte si le fichier est verrouillé.

Ne commiter que sur demande.
