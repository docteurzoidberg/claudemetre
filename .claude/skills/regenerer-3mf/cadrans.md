# 3MF des cadrans

```
fond-jauge (modèle, scripts/fond_jauge.py)
   │ Dériver (lien mis à jour)
   ▼
fond-jauge-session / fond-jauge-semaine   couleurs : variante() + cadran_dxf/
   │ scripts/export_cadrans.py   (Fusion, par MCP)
   ▼
%TEMP%\claudemetre\export\<variante>\{fond,echelle,zone,texte}.stl + export.json
   │ uv run cadran_3mf.py        (WSL, dans design/fusion)
   ▼
design/fusion/print/<variante>.3mf + <variante>_apercu.png
```

Le 3MF est un **projet Snapmaker Orca** (le trancheur de l'utilisateur, pas
OrcaSlicer) : **un objet à 4 pièces, une par couleur** (fond, echelle, zone,
texte), face visible contre le plateau, au centre du plateau de la U1.
- Pas 4 objets : hors projet, Snapmaker Orca croit en pouces tout objet de
  moins de 9 mm³ (zone 3,4 mm³, texte 6 à 8 mm³).
- Réglages : le profil U1 de l'utilisateur, gabarit `u1-4pla-cadrans` de la
  bibliothèque commune (`~/3d/impression-3d/gabarits/u1-4pla-cadrans.json`),
  avec les réglages d'impression du cadran (`REGLAGES` de `cadran_3mf.py` : couches de 0,2
  première comprise, première couche à 0,42 mm et lente, Arachne, 100 %,
  tour de purge). La première couche est un réglage global : d'où un projet
  complet plutôt que des réglages d'objet.
- **Aucune pièce attribuée à un filament** : l'utilisateur choisit filaments et
  têtes au moment d'imprimer (l'ordre des bobines sur les têtes change).
- Écriture du 3MF : `imp3d.threemf` (skill global `impression-3d`), sans
  bloc `<plate>` depuis le 02/11/2026.
- Si le profil U1 de l'utilisateur change (autre procédé, nouvelle version
  de Snapmaker Orca) : refaire le gabarit depuis un de ses projets récents
  relu (`gabarit.charger('projet.3mf').enregistrer(...)`, skill
  `impression-3d`), sans se servir de son fichier tel quel.

Charger d'abord le skill `fusion360` (Fusion lancé, MCP actif). Rappel : **ne
jamais enregistrer les designs Fusion soi-même**, le demander à l'utilisateur.

## 1. Répercuter la modification dans les variantes

Partir de ce qui a changé :

| Changement | À faire avant l'export |
| --- | --- |
| Graduations, textes, couleurs (`design/dials/so45_print.py`, `dial_so45_spec.json`) | `uv run so45_print.py` (dans `design/dials` : contrôles). Puis pour chaque cadran : `uv run cadran_dxf.py dark <session\|semaine>` (dans `design/fusion`), recopier `cadran_dxf/` dans `%TEMP%\claudemetre\cadran_dxf\`, ouvrir la variante (document actif), lancer `variante()` de `scripts/fond_jauge.py` (copié dans le Temp). Une variante à la fois : `variante()` refuse le DXF de l'autre cadran. Style : celui du `cadran.json` actuel (`dark`) |
| Plaque, épaisseurs, lamages, piliers (design `fond-jauge`) | Modifier le paramètre favori dans `fond-jauge` (`r_plaque`, `entraxe_trous`, `d_pilier`, `jeu_pilier`, `ep_face`…) (et la cote du dépôt : `dial_so45_spec.json`, défaut de `scripts/fond_jauge.py`, puis `uv run so45_print.py`). L'utilisateur enregistre `fond-jauge`. Puis **fermer** les variantes et `fond-jauge` (`close(False)`, rien d'utile en suspens) : ouvertes avec leur source, `updateAllReferences()` ne recalcule pas la dérivation. Rouvrir chaque variante seule, `doc.updateAllReferences()`, et relire dans un **script suivant** le paramètre `_Ref` changé et la géométrie (ex. diamètres des cylindres du fond). Fait ainsi le 29/10/2026 (piliers Ø 4 → 5) |
| Une variante modifiée directement | Rien |

Puis demander à l'utilisateur d'enregistrer les variantes modifiées.
L'export prend l'état ouvert, même non enregistré, mais le signale.

## 2. Exporter depuis Fusion

```bash
. ./prive.env
cp design/fusion/scripts/export_cadrans.py "$WIN_TEMP/claudemetre/"
```

Puis `fusion_mcp_execute` (script) avec le chargeur :

```python
import os
def run(ctx):
    p = os.path.join(os.environ['TEMP'], 'claudemetre', 'export_cadrans.py')
    ns = {'__file__': p}
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), ns)
    ns['run'](ctx)
```

Les variantes fermées sont ouvertes en arrière-plan puis refermées (le
document actif ne change pas). Arrêts possibles :
- « dérivation périmée » : revenir à l'étape 1 (ligne `fond-jauge`) ;
- « fonctions en erreur » : à corriger dans Fusion ;
- « ATTENTION : … non enregistré » : rappeler l'enregistrement.

## 3. Écrire les 3MF

```bash
cd design/fusion && uv run cadran_3mf.py
```

**Cadrans verrouillés** (`design/fusion/FICHIERS_VALIDES.md`, depuis le
02/11/2026 : les deux `print/*.3mf`, ré-enregistrés par l'utilisateur dans
Snapmaker Orca avec ses filaments) : `cadran_3mf.py` ne les réécrit pas
(`VALIDE GARDE`) ; la nouvelle version et son aperçu vont dans
`%TEMP%\claudemetre\valides_nouveaux\`. Pour la livrer : la montrer à
l'utilisateur, et seulement à sa demande `imp3d valides retirer design/fusion
print/<variante>.3mf`, relancer, puis `imp3d valides ajouter …` une fois le
fichier ré-enregistré. État : `imp3d valides verifier design/fusion`.

Résumé attendu (plaque actuelle) : 1 objet, 4 pièces par fichier, 40,8 ×
36,7 × 2,00 mm, couleurs à 0,80 mm d'épaisseur, une couleur par pièce en
hexadécimal.
« fond : 21 arêtes de contact » est normal : la zone rouge touche le bout de
graduations, le fond y a une épaisseur nulle (maillage fermé, le trancheur
s'en accommode ; lib3mf le dit non manifold pour cette raison).
Erreurs : maillage ouvert, volume différent du corps Fusion (unités), couleur
pas à fleur de la face, largeur hors 30-60 mm.

## 4. Vérifier et rendre compte

- Lire `print/<variante>_apercu.png` : la face doit se lire **à l'endroit**
  (pas en miroir), graduations et textes à leur place.
- Donner à l'utilisateur le chemin Windows : `WSL_PROJET` de `prive.env`, suivi de
  `\design\fusion\print\`,
  et la couleur de chaque pièce (pour attribuer les bobines).
- Dans le trancheur : un objet, ses 4 pièces dans la liste des objets ; un
  filament par pièce (texte et échelle peuvent partager la même bobine).
  Ne pas retourner l'objet.
- Dans Snapmaker Orca, couche 1 vue de dessous : décocher « Seams » dans la
  légende (les points blancs sont les jointures, pas des défauts) ; la barre
  du % (0,5 mm) doit être tracée.
- Contrôle facultatif par tranchage, sans ouvrir l'interface : skill global
  `impression-3d` (commande `imp3d`, Snapmaker Orca en ligne de commande) :
  `imp3d tranche print/<variante>.3mf --garder`, puis
  `imp3d gcode <G-code affiché> --couches` (têtes par couche, emprise centrée
  sur 135,5 ; 136). Vérifié le 02/11/2026 sur `fond-jauge-session.3mf`
  (enregistré dans l'interface avec ses filaments) : 2 s, 10 couches,
  12 min 30, 3,21 g. Un fichier enregistré dans l'interface a un bloc
  `<plate>` qui fait planter la ligne de commande (code 5) : `imp3d` le
  retire de sa copie de travail (le 3MF n'est pas touché). Le générateur
  n'en écrit plus (02/11/2026 : cadrans régénérés dans une copie,
  équivalents aux anciens, mêmes couches, poids et emprise au tranchage).
  La version « 01.10 » de la ligne de commande se contourne par la variable
  `SNAPMAKER_ORCA_ALLOW_NEWER_FILE=1` ; le code 5 venait du bloc `<plate>`,
  pas du rendu OpenGL.
