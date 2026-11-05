---
name: regenerer-docs-en
description: "Reporte dans docs/en/ les modifications du README.md et des docs françaises (docs/*.md) du claudomètre, en ne retraduisant que les passages changés. À utiliser après une modification du README ou de docs/, quand le hook pre-push refuse un push (« docs françaises en avance sur leur version anglaise »), ou quand on demande de mettre à jour la version anglaise."
---

# Version anglaise des docs

Le français fait foi. `docs/en/` en est la traduction, sous des noms anglais : la correspondance
n'est écrite que dans `.githooks/docs-en-retard`.

## 1. Repérer ce qui a changé

```bash
.githooks/docs-en-retard
git status --short -- README.md docs/
```

La première commande liste les docs commitées en avance, avec le dernier commit de leur version
anglaise (`doc_fr doc_en commit`). La seconde montre le travail pas encore commité. Pour une doc
qui n'apparaît que là, ce commit se lit avec `git log -1 --format=%h -- <doc_en>`.

## 2. Lire le diff, pas toute la doc

```bash
git diff <commit> -- <doc_fr>
```

Ce diff couvre aussi ce qui n'est pas encore commité. Rien d'autre n'est à retraduire : ne pas
reformuler les paragraphes anglais que le diff ne touche pas.

## 3. Reporter dans la doc anglaise

- Même structure que le français : titres, ordre, tableaux, listes.
- Ne pas traduire les identifiants, commandes, chemins, noms de composants Fusion et d'entités
  Home Assistant : `plaque_bossage_fusible`, `binary_sensor.claude_actif`.
- Liens : vers la doc anglaise quand elle existe (`specification.md`), sinon vers le fichier du
  dépôt depuis `docs/en/` (`../../host/README.md`). La première ligne reste le lien vers le français.
- Une question ouverte cochée ou retirée en français l'est aussi en anglais.

Vocabulaire déjà en place :

| Français | Anglais |
| --- | --- |
| coque | shell |
| platine | faceplate |
| plaquette | nameplate |
| plaque de flanc | side plate |
| cadran, jauge, aiguille | dial, gauge, needle |
| témoin, voyant | indicator |
| afficheur 7 segments | 7-segment display |
| visière | visor |
| carte à borniers | terminal board |
| maquette, éclaté | mockup, exploded view |
| FHC, CHC | countersunk, socket head |

## 4. Contrôler

```bash
grep -c '^#' <doc_fr> <doc_en>
```

Le nombre de lignes doit être le même (les commentaires `#` des blocs de code comptent aussi).
Relire ensuite le diff de la doc anglaise : ce contrôle ne voit que la structure.

## 5. Finir

Ne commiter que sur demande. La doc anglaise peut partir dans le même commit que le français ou
dans un commit suivant : le hook `pre-push` ne regarde que l'ordre des commits, pas le contenu, et
ne voit donc pas une traduction incomplète.

Une correction sans effet sur l'anglais (faute de frappe, accent) n'a rien à reporter : pousser
avec `git push --no-verify`. Le hook ne la signale plus une fois poussée.
