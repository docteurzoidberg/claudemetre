# Scripts de construction du design Fusion `claudometre`

Scripts Python exécutés dans Fusion 360 par le serveur MCP (skill `fusion360`),
dans l'ordre de construction du design. Ce sont des scripts **de construction,
à usage unique** : les relancer crée des doublons. Ils servent de référence
(cotes, méthode) et de point de départ pour une reconstruction ; ils
correspondent au modèle, mais n'ont pas été rejoués de bout en bout.

Le témoin CLAUDE n'en fait pas partie : le composant `claude` et sa découpe dans
l'esquisse `passages` de la platine (centre à 26 sous l'origine, 34,8 × 13,8,
trous Ø 3,4 à 42 d'entraxe) viennent du générateur, voir
[docs/temoin.md](../../../docs/temoin.md).

Pour les exécuter : copier ce dossier dans `%TEMP%\claudemetre\` (avec
`../../plaquettes/dxf/` en `dxf\`), puis lancer
par un chargeur de quelques lignes :

```python
import os
def run(ctx):
    p = os.path.join(os.environ['TEMP'], 'claudemetre', 'coque.py')
    ns = {'__file__': p}
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), ns)
    ns['run'](ctx)
```

| Script | Rôle |
| --- | --- |
| `lib.py` | outils communs : paramètres, esquisses cotées, perçages, congés, miroirs |
| `coque.py` | paramètres de la coque + coque (rebord, chanfrein à 45°, piliers, logements d'inserts) |
| `platine.py` | paramètres + platine (passages, fenêtre, bossages d'inserts, fraisures) |
| `place_parts.py` | apparences, insertion des SO-45 et du TM1637 par liaisons sur origines paramétrées |
| `vis_courtes.py` | variantes CHC M3×12 et M3×6 de la vis CHC M3×16 (`fix()` pour refaire un enregistrement manqué) |
| `tm1637_jaune.py` | segments de l'afficheur passés au jaune (nouvelle version du modèle) |
| `tm1637_sans_connecteur.py` | connecteur coudé retiré du modèle de l'afficheur (v3) ; à lancer `claudometre` fermé, puis `getLatestVersion()` dans l'assemblage |
| `visserie.py` | inserts et vis liés à leurs perçages (`run_groups([...])`) |
| `visiere.py` | rainure en U dans la platine + visière ; limite les perçages de l'afficheur à l'insert |
| `plaquettes2.py` | plaquettes centrées sur leur origine, placées par liaison, texte incrusté (DXF) |
| `plaquettes3.py` | `epaisseur()` passe `plaq_ep` à 1,8, `hauteur()` passe `plaq_H` à 8 ; `texte()` remplace le texte des trois plaquettes d'après les DXF, sans toucher aux liaisons ni aux vis. Trop long pour le délai du serveur : il va au bout malgré « The operation timed out », sonder avant de relancer |
| `visiere_pente.py` | pente de l'avant des joues de la visière |
| `fond_jauge.py` | design à part `fond-jauge`, le modèle des cadrans imprimés : plaque du cadran d'origine mesurée, esquisse de repères (axe, échelle d'origine, fenêtre) ; `canvas()` ajoute la photo redressée ; `imprime()` ajoute le cadran imprimé (renfort au dos, lamages des piliers). `derive()` crée une variante (nouveau design dérivé du modèle enregistré) et `variante()` y applique les couleurs d'après les DXF de `../cadran_dxf.py` (à copier dans `%TEMP%\claudemetre\cadran_dxf\`) ; relancée, elle remplace les couleurs. `plaque_parametree()` (après le premier tirage) : rayon et entraxe des trous en paramètres favoris `r_plaque`, `entraxe_trous` |
| `export_cadrans.py` | **export, relançable** : STL des composants de couleur des variantes `fond-jauge-*` pour `../cadran_3mf.py` (3MF à imprimer) |
| `fenetres_flancs.py` | fenêtres des flancs et logements d'inserts des plaques de flanc ; `inserts()` pose les 8 inserts dans `visserie` |
| `plaque_flanc.py` | plaque de flanc générique (composant `plaque_flanc`) placée sur les deux flancs ; ses cotes commandent la fenêtre et les inserts ; `vis()` pose les 8 vis |
| `plaque_encastree.py` | plaque à fleur du flanc : feuillures, nervures d'appui, piliers liés à la fenêtre (`pilier_z`), inserts reliés au fond de la feuillure |
| `plaque_saillie.py` | `saillie()` : dépassement de la plaque (`plaque_saillie`, 1 mm), la coque ne change pas ; `alignement()` : `plaque_bord` calculé pour mettre les vis de plaque à `vis_z` (plaque de 86) |
| `visserie_stock.py` | visserie adaptée au stock : `pilier()` (perçages de 10 pour une FHC M3×12), `plaques()` (lamages et CHC M3×6), `modele_fhc12()` (modèle `vis_FHC_M3x12`, enregistré), `remplace_fhc(ctx, id)` (FHC restantes passées en M3×12) |
| `cadrans_assemblage.py` | `fond-jauge-session` et `fond-jauge-semaine` (déjà insérés) liés à leur SO-45, profondeur `jauge_appui` |
| `support_carte.py` | `logements()` creuse le fond de la coque, `clips()` dérive et place les trois clips, `carte()` insère `mrd076a_esp32_s3` (paramètres `carte_*`, `clip_*`) |
| `plaque_bossage.py` | `run()` construit `plaque_bossage` et la pose sur le flanc droit, à la place de `plaque_flanc:1` masquée ; `pose_connecteur(ctx, nom)` insère un LP-16 de `models/` dans le composant, bride sur le coin, ergot vers le haut ; `visserie_connecteur()` pose 4 inserts et 4 FHC M3×12 dans le composant ; `regroupe()` y a rangé ces pièces dans `claudometre`, une seule fois. Dans le design, l'esquisse `face` garde cinq cercles en construction que le script ne trace pas |
| `plaque_bossage_fusible.py` | `run()` construit `plaque_bossage_fusible` sur le flanc droit ; `pose_lp16()` y met le LP-16, 4 inserts et 4 FHC M3×12 (long : « The operation timed out », mais il va au bout, sonder avant de relancer) ; `pose_fusible()` le porte-fusible ; `affiche()` la montre à la place de `plaque_bossage` ; `controle()` (lecture seule) cherche les interférences avec les pièces voisines et entre ses pièces |
| `check_bossage.py` | sonde : `run()` (lecture seule) interférences et jeux du connecteur posé ; `essai_usbc()` fait de même avec l'USB-C, puis lève une exception pour tout annuler. La ligne `jeu FHC / arrière du connecteur` compte aussi la bride et affiche 0 : mesurer le corps arrière seul |
| `check_support.py` | sonde, lecture seule : collisions et jeux de la carte et des clips. Pour la coque, qui englobe tout, le tri par boîtes ne vaut rien : seules 25 paires sont mesurées |
| `accroche.py` | accroche murale : `run()` pose les paramètres `accroche_*` et deux trous de serrure dans le fond de la coque (grand trou, fente, miroir) ; `mi_hauteur()` amène les vis à z = 0 |
| `patron.py` | patron de perçage de la planche : plaque mince, trous au centre des grands trous des fentes (composant `patron`, paramètres `patron_*`) |
| `export_patron.py` | **export, relançable** : STL et `patron.json` pour `../patron_3mf.py` (3MF à imprimer) |
| `export_coque.py` | **export, relançable** : STL et `coque.json` pour `../coque_3mf.py` (3MF à imprimer) |
| `export_plaquettes.py` | **export, relançable** : un STL par corps et `export.json` pour `../plaquettes_3mf.py` (3MF à imprimer) |
| `export_platine.py` | **export, relançable** : STL et `platine.json` pour `../platine_3mf.py` (3MF à imprimer) |
| `export_visiere.py` | **export, relançable** : STL et `visiere.json` pour `../visiere_3mf.py` (3MF à imprimer) |
| `export_plaques.py` | **export, relançable** : STL de chaque plaque (`KEYS`), en repère du composant, et `plaques.json` avec sa hauteur mesurée, pour `../plaques_3mf.py` (3MF à imprimer) |
| `export_clips.py` | **export, relançable** : STL des trois clips, en repère du composant, et `clips.json` pour `../clips_3mf.py` (3MF à imprimer) |
| `export_blender.py` | **export, relançable, lecture seule** : maillages des corps visibles, en place, avec les normales de Fusion, pour la maquette `jj_fusion` (`claudometre.bin`, `claudometre.json`, à copier dans `../blender/`) ; un corps par segment de l'afficheur. Sa fonction `complet` exporte aussi les pièces internes, pour la page `maquette/` (à copier dans `../web/`, hors dépôt) |
| `check_plaquettes.py` | sonde, lecture seule : cotes, texte centré et à fleur, couleurs, et ce qu'il y a dans l'axe derrière les vis |
| `check_accroche.py` | sonde : `chemin()` (lecture seule) cherche les collisions sur le chemin de la tête, `essai()` change la tête et la tige puis remet les valeurs |
| `check.py`, `check_visserie.py` | sondes : jeux et interférences (lents sur tout l'assemblage) |
