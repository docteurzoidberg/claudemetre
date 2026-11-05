---
name: nouvelle-plaque
description: "Ajoute une plaque de flanc au claudomètre (autre connecteur, autre forme, variante d'une plaque existante) et la fait entrer partout : composant Fusion complet sur l'interface de plaque_flanc, exports, 3MF, page maquette/, rendus et docs. À utiliser dès qu'on demande une nouvelle plaque, un autre connecteur sur le flanc, ou une variante de plaque_bossage ou de plaque_bossage_fusible."
---

# Nouvelle plaque de flanc

Modèle à suivre : `plaque_bossage_fusible` (`design/fusion/scripts/plaque_bossage_fusible.py`). Interface et cotes :
`design/fusion/README.md`, section « Interface des plaques de flanc ».

## Règles

- **Une plaque = un composant complet** : la plaque, ses connecteurs, leurs inserts et leur visserie. Jamais à la
  racine ni dans `visserie`, où seules restent les 4 CHC M3×6 du flanc.
- **Toutes les plaques restent dans `claudometre`.** On en affiche une par flanc et on masque les autres.
- **Une copie, jamais une retouche** : ne pas modifier les plaques existantes.
- **Rien ne change sur la coque ni la platine.** Contour, partie logée, dépassement et vis viennent des paramètres
  de `plaque_flanc`.
- **Plaque asymétrique :** une variante par flanc. Sur le flanc gauche, ajouter 180° autour de Z dans la liaison.
- **Visserie :** celle du stock (`docs/cahier-des-charges.md`). Dire « inserts M3 », pas « inserts de 5 mm ».

Si la forme reste à choisir, proposer d'abord une maquette : plus rapide à comparer que le design Fusion.

## 1. Pièces du commerce

Pour chaque pièce nouvelle :
- copier le STEP dans `models/` du projet Fusion, même s'il existe ailleurs ;
- `design/references/<pièce>/` : STEP et `README.md` avec les cotes ;
- une ligne dans `design/references/grabcad.md` si le modèle vient de GrabCAD, et dans l'arborescence de `CLAUDE.md`.

Mesurer sur le modèle, ne pas supposer : perçages, fraisures, filets. Ce qui reste à confirmer sur la pièce reçue
va dans les questions ouvertes.

## 2. Modéliser

Charger le skill `fusion360`. Étape par étape : montrer une vue après chaque étape et relire les messages de
l'utilisateur avant d'enchaîner. L'enregistrement lui revient : le rappeler en fin d'étape, puis vérifier le nom et
le dossier du design.

Script `design/fusion/scripts/plaque_<nom>.py`, à partir de `plaque_bossage_fusible.py` : `run()` construit le
composant, `pose_<pièce>()` insère les pièces, `controle()` cherche les interférences.

- Repère de la plaque sur le flanc droit : origine (97 ; 21,25 ; 0), X plaque = Y monde − 21,25, Y plaque = Z monde,
  Z plaque = X monde − 97.
- Insérer directement dans le composant. `Occurrence.moveToComponent(cible)` déplace une occurrence déjà posée, en
  gardant sa position, et ajoute une fonction à la timeline.
- `root.allJoints` est un `JointVector` : pas de `.count`.
- Un script long renvoie « The operation timed out » et va pourtant au bout : sonder avant de relancer.
- Lever une exception à la fin d'un script annule tout : c'est la façon de faire un essai à blanc.
- `controle()` : filtrer par la boîte du composant, sinon il dépasse le délai. Seuls les inserts M3 recoupent la
  plaque, c'est normal.
- Vue : `viewport.fit()`, puis `setExtents` avec `isFitView = False`.

## 3. Exports et 3MF

| Fichier | À ajouter |
| --- | --- |
| `design/fusion/scripts/export_blender.py` | `<plaque>:1` dans `PLAQUES`, `<plaque>:1+insert` dans `SKIP` ; la pose d'un connecteur autre que le LP-16 si la maquette en a besoin |
| `design/fusion/scripts/export_plaques.py` | `<plaque>` dans `KEYS`, et ses paramètres dans la liste du `for` |
| `design/fusion/plaques_3mf.py` | une entrée dans `PLAQUES` : filament, supports, saillie, jeu. Si la forme n'est pas paramétrée, comme `plaque_bossage_fusible`, passer sa saillie par `plaques.json` |

Puis skill `regenerer-3mf`. `plaques_3mf.py` refuse toute face en surplomb hors du creux.

## 4. Page `maquette/`

| Fichier | À ajouter |
| --- | --- |
| `maquette/pack.py` | ses pièces dans `PIECES` et `OPTIONS` ; `classe()` et `plaque()`, qui ne connaissent que deux plaques à connecteur (`f`) : passer à une table pour une troisième ; l'axe du connecteur (`AXE_FUSIBLE`) ; la fiche et le câble (`fiche_a_45()`) |
| `maquette/main.js` | une entrée dans `PLAQUES` (`sans`, `plaques`, `connecteur`, `visserie`, avec le compte de vis) ; un groupe dans `GROUPES` pour une pièce d'un genre nouveau ; la plaque par défaut, à la ligne `let plaque` |
| `maquette/index.html` | sa touche `data-plaque` dans `#plaques` |
| `maquette/README.md` | la valeur de `?plaque=` |

Puis skill `regenerer-maquette`, avec une capture de la nouvelle plaque.

## 5. Rendus

`design/blender/variants6.py` : ajouter la racine aux plaques classées (`racine in (...)`). Le reste seulement si
l'utilisateur veut la plaque sur les rendus : skill `rendu-maquette`.

## 6. Docs

- `design/fusion/README.md` : sous-section de la plaque (cotes, contrôle) et ligne dans « Fichiers à imprimer ».
- `design/fusion/scripts/README.md` : le script.
- `docs/cahier-des-charges.md` : décision et questions ouvertes.
- `docs/maquettes.md` : la liste des plaques de la page.
- Puis skill `regenerer-docs-en`.

Ne commiter et ne pousser que sur demande.
