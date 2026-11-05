# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""3MF prêts à imprimer des plaques de flanc, à partir des STL de scripts/export_plaques.py.

Usage : uv run plaques_3mf.py [dossier d'export]
  (défaut : le Temp Windows, %TEMP%/claudemetre/export/plaques)
  → print/plaque_flanc.3mf : PETG noir (gabarit u1-petg, filament 3), sans support.
  → print/plaque_bossage.3mf : PETG kaki (filament 4), supports en arbre dans le creux, en kaki.
  Une plaque par fichier, face d'appui sur le plateau, face visible vers le haut, au centre du plateau.

Pourquoi des supports dans `plaque_bossage` : le plafond du creux, sous la face du connecteur, est à
30° de l'horizontale, le seuil du profil. Ils ne coûtent que 4 min et 1 g, sans tour de purge, et
gardent propre la lèvre arrière du perçage Ø 16,5 (0,1 mm de jeu avec le fût). Le plafond sous la pente, à
45°, s'imprime seul.

Contrôles : maillage fermé, volume égal à celui du corps Fusion (à la tessellation près), cotes de la
plaque, et aucune face en surplomb hors du creux : les supports ne touchent aucune surface visible.
"""
import json
import sys
from pathlib import Path

from prive import WIN_TEMP

import numpy as np

sys.path.insert(0, str(Path.home() / "3d/impression-3d"))
from imp3d import gabarit, maillage, threemf  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = WIN_TEMP / "claudemetre/export/plaques"
GABARIT = "u1-petg"
NOIR, KAKI = 3, 4                           # têtes du PETG noir et kaki, comme dans la coque enregistrée dans Orca
COULEUR_KAKI = "#547117"
SURPLOMB = -0.5                             # composante z de la normale : plus de 30° sous la verticale
PLAQUES = {
    # saillie : paramètre du dépassement ; jeu : l'arête du bossage est arrondie, elle n'atteint pas sa cote
    "plaque_flanc": {"filament": NOIR, "supports": None, "saillie": "plaque_saillie", "jeu": 0.01},
    "plaque_bossage": {"filament": KAKI, "supports": "tree(auto)", "saillie": "bossage_saillie", "jeu": 0.2},
}


def controle(nom, r, m, e, info):
    tri = m.V[m.T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if abs(vol - e["volume"]) > 0.01 * e["volume"]:
        raise SystemExit(f"{nom} : volume {vol:.1f} mm³ au lieu de {e['volume']}")
    a = np.sort(m.T[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    if (np.unique(a, axis=0, return_counts=True)[1] != 2).any():
        raise SystemExit(f"{nom} : maillage ouvert")
    attendu = np.array([info["plaque_P"], info["plaque_H"], info["plaque_ep"] + info[r["saillie"]]])
    if (np.abs(m.taille - attendu) > [0.01, 0.01, r["jeu"]]).any():
        raise SystemExit(f"{nom} : dimensions {m.taille} au lieu de {attendu}")
    sous = n[:, 2] < SURPLOMB * np.linalg.norm(n, axis=1)
    sous &= tri[:, :, 2].max(axis=1) > 1e-3
    limite = info["fen_P"] / 2 if r["supports"] else 0
    if sous.any() and np.abs(tri[sous][:, :, 0]).max() > limite + 1e-3:
        raise SystemExit(f"{nom} : surplomb à x = {np.abs(tri[sous][:, :, 0]).max():.1f}, hors du creux")
    return vol


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    info = json.loads((src / "plaques.json").read_text(encoding="utf-8"))
    for nom, r in PLAQUES.items():
        e = info["plaques"][nom]
        m = maillage.lire_stl(src / e["stl"])
        m = m.deplace([-m.centre[0], -m.centre[1], -m.mini[2]])
        vol = controle(nom, r, m, e, info)

        g = gabarit.charger(GABARIT).filaments([None, None, None, (COULEUR_KAKI, None, None)])
        if r["supports"]:
            g.supports(r["supports"], filament=r["filament"], interface=r["filament"])
        projet = threemf.Projet(g)
        objet = projet.objet(nom, filament=r["filament"])
        objet.piece(m, nom)
        projet.placer(objet)
        sortie = HERE / "print" / f"{nom}.3mf"
        projet.ecrire(sortie)
        print(f"{sortie.relative_to(HERE)} : {m.taille[0]:.1f} × {m.taille[1]:.1f} × {m.taille[2]:.2f} mm, "
              f"{len(m.T)} triangles, {vol / 1000:.2f} cm³, version {info['version']}"
              f"{' + modifications non enregistrées' if info['non_enregistre'] else ''}")
        for niveau, message in threemf.verifier(sortie):
            print(niveau, message)


if __name__ == "__main__":
    main()
