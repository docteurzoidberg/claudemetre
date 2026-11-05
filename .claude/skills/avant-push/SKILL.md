---
name: avant-push
description: "Vérifie que le dépôt du claudomètre est prêt à être poussé : maquette à la version du design, version anglaise des docs, cahier des charges, artefacts, hooks actifs. À utiliser quand on demande de pousser, ou de vérifier ce qui reste à faire avant un push. Le skill rend compte et ne pousse pas de lui-même."
---

# Avant de pousser

Les hooks Git bloquent les valeurs privées et les docs anglaises en retard. Ce skill couvre ce qu'ils ne voient pas.

## 1. Ce qui part

```bash
git status --short
git log --oneline @{u}..
git diff --stat @{u}..
git config --get core.hooksPath
```

La dernière commande doit répondre `.githooks` : sinon, activer les hooks (`CLAUDE.md`). Signaler ce qui n'est pas
commité : ça ne partira pas.

## 2. Vérifier

| Contrôle | Comment | Si ce n'est pas à jour |
| --- | --- | --- |
| Docs anglaises | `.githooks/docs-en-retard` ne répond rien | skill `regenerer-docs-en` |
| Maquette | version du GLB égale à celle de `claudometre` (étape 1 de `regenerer-maquette`) | skill `regenerer-maquette` |
| Page `maquette/` | les commits sortants qui touchent `maquette/` sont aussi sur l'artefact | étapes 4 et 5 de `regenerer-maquette` |
| 3MF | les commits sortants qui changent une pièce ont leur 3MF | skill `regenerer-3mf` |
| Cahier des charges | `docs/cahier-des-charges.md` reprend les décisions sortantes, et ses questions ouvertes sont à jour | le compléter, puis `regenerer-docs-en` |
| État du projet | la section « État » de `CLAUDE.md` reste vraie | la corriger |
| Autres artefacts | sources de `ARTEFACTS.md` touchées par les commits sortants : `design/gallery/`, `design/cablage/` | les republier sur leur URL |

Si Fusion n'est pas lancé, la version de `claudometre` n'est pas lisible : le dire, sans conclure que la maquette
est à jour. Le GLB ne compte que si le design a changé : il n'y a rien à refaire pour un changement de firmware ou
de doc.

## 3. Rendre compte

Un tableau : contrôle, résultat, ce qu'il reste à faire. Les mises à jour demandent l'accord de l'utilisateur quand
elles sont longues ou passent par Fusion.

Ne pousser que s'il l'a demandé, et une fois les points ouverts réglés ou acceptés par lui. `git push --no-verify`
reste son choix, par exemple pour une correction du français sans effet sur l'anglais.
