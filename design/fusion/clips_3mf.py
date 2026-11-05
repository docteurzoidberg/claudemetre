# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""3MF prêt à imprimer des trois clips du support de carte, à partir des STL de scripts/export_clips.py.

Usage : uv run clips_3mf.py [dossier d'export]
  (défaut : le Temp Windows, %TEMP%/claudemetre/export/clips)
  → print/clips.3mf : projet Snapmaker Orca, PETG noir (gabarit u1-petg, filament 3), les trois à la fois,
    sur le flanc, sans support.

Sur le flanc, les parois suivent le profil : la zone qui fléchit (1,4 à 1,8 mm) et le bras du crochet
(1,6 mm) sont faits de deux parois pleines, sans remplissage, et le dessous à coller sort lisse. Les ailes
se posent du côté de leur oreille : de l'autre, 70 mm² seraient en surplomb.

Contrôles : maillages fermés, volume égal à celui des corps Fusion (à la tessellation près), cotes des
clips, surplomb négligeable (moins de 30° de l'horizontale) : un rebord de 3 mm² sur les ailes.
"""
import json
import sys
from pathlib import Path

from prive import WIN_TEMP

import numpy as np

sys.path.insert(0, str(Path.home() / "3d/impression-3d"))
from imp3d import gabarit, maillage, threemf  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = WIN_TEMP / "claudemetre/export/clips"
GABARIT = "u1-petg"
FILAMENT = 3                                # tête du PETG noir, comme dans la coque enregistrée dans Orca
PAS_Y = 20                                  # entre deux clips sur le plateau
SURPLOMB_MAX = 5                            # mm²


def y_mini_en_bas(V):
    return np.c_[V[:, 0], -V[:, 2], V[:, 1]]


def y_maxi_en_bas(V):
    return np.c_[V[:, 0], V[:, 2], -V[:, 1]]


# Rotations autour de X, pas de miroir : l'oreille des ailes est au y mini de clip_aile, au y maxi de son miroir.
CLIPS = {
    "clip_aile": (y_mini_en_bas, "clip_aile_l"),
    "clip_milieu": (y_mini_en_bas, "clip_mil_l"),
    "clip_aile_miroir": (y_maxi_en_bas, "clip_aile_l"),
}


def controle(nom, m, e, largeur, longueur):
    tri = m.V[m.T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    aire = np.linalg.norm(n, axis=1) / 2
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if abs(vol - e["volume"]) > 0.01 * e["volume"]:
        raise SystemExit(f"{nom} : volume {vol:.1f} mm³ au lieu de {e['volume']}")
    a = np.sort(m.T[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    if (np.unique(a, axis=0, return_counts=True)[1] != 2).any():
        raise SystemExit(f"{nom} : maillage ouvert")
    if abs(m.taille[0] - longueur) > 0.01 or abs(m.taille[2] - largeur) > 0.01:
        raise SystemExit(f"{nom} : dimensions {m.taille} au lieu de {longueur} de long et {largeur} de large")
    sous = (n[:, 2] < -0.866 * 2 * aire) & (tri[:, :, 2].max(axis=1) > 1e-3)
    if aire[sous].sum() > SURPLOMB_MAX:
        raise SystemExit(f"{nom} : {aire[sous].sum():.0f} mm² en surplomb")
    return vol


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    info = json.loads((src / "clips.json").read_text(encoding="utf-8"))
    projet = threemf.Projet(gabarit.charger(GABARIT))
    cx, cy = projet.gabarit.centre()
    for i, (nom, (pose, largeur)) in enumerate(CLIPS.items()):
        e = info["clips"][nom]
        brut = maillage.lire_stl(src / e["stl"])
        m = maillage.Maillage(pose(brut.V), brut.T)
        m = m.deplace([-m.centre[0], -m.centre[1], -m.mini[2]])
        vol = controle(nom, m, e, info[largeur], info["clip_L"])
        objet = projet.objet(nom, filament=FILAMENT)
        objet.piece(m, nom)
        projet.placer(objet, position=(cx, cy + (1 - i) * PAS_Y))
        print(f"{nom:17s} {m.taille[0]:.1f} × {m.taille[1]:.1f} × {m.taille[2]:.1f} mm, {vol / 1000:.2f} cm³")
    sortie = HERE / "print" / "clips.3mf"
    projet.ecrire(sortie)
    print(f"{sortie.relative_to(HERE)}, version {info['version']}"
          f"{' + modifications non enregistrées' if info['non_enregistre'] else ''}")
    for niveau, message in threemf.verifier(sortie):
        print(niveau, message)


if __name__ == "__main__":
    main()
