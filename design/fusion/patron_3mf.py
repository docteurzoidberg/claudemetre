# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""3MF prêt à imprimer du patron de perçage, à partir du STL de scripts/export_patron.py.

Usage : uv run patron_3mf.py [dossier d'export]
  (défaut : le Temp Windows, %TEMP%/claudemetre/export)
  → print/patron.3mf : projet Snapmaker Orca, PETG (gabarit u1-petg, filament 2), à plat, sans
    support, au centre du plateau de la U1.

Contrôles : maillage fermé, volume égal à celui du corps Fusion (à la tessellation près),
dimensions égales à celles de la coque.
"""
import json
import sys
from pathlib import Path

from prive import WIN_TEMP

import numpy as np

sys.path.insert(0, str(Path.home() / "3d/impression-3d"))
from imp3d import gabarit, maillage, threemf  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = WIN_TEMP / "claudemetre/export"
GABARIT = "u1-petg"
FILAMENT = 2                                # PETG noir


def controle(m, info):
    tri = m.V[m.T]
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if abs(vol - info["volume"]) > 0.01 * info["volume"]:
        raise SystemExit(f"volume {vol:.1f} mm³ au lieu de {info['volume']}")
    e = np.sort(m.T[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    if (np.unique(e, axis=0, return_counts=True)[1] != 2).any():
        raise SystemExit("maillage ouvert")
    attendu = np.array([info["coque_L"], info["coque_H"], info["patron_ep"]])
    if np.abs(m.taille - attendu).max() > 0.01:
        raise SystemExit(f"dimensions {m.taille} au lieu de {attendu}")
    return vol


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    info = json.loads((src / "patron.json").read_text(encoding="utf-8"))
    brut = maillage.lire_stl(src / "patron.stl")
    # Rotation autour de X (pas de miroir) : la face plate, à y = patron_y, passe sur le plateau.
    V = np.c_[brut.V[:, 0], brut.V[:, 2], info["patron_y"] - brut.V[:, 1]]
    m = maillage.Maillage(V, brut.T)
    m = m.deplace([-m.centre[0], -m.centre[1], -m.mini[2]])
    vol = controle(m, info)

    projet = threemf.Projet(gabarit.charger(GABARIT))
    objet = projet.objet("patron", filament=FILAMENT)
    objet.piece(m, "patron")
    projet.placer(objet)
    sortie = HERE / "print" / "patron.3mf"
    projet.ecrire(sortie)
    print(f"{sortie.relative_to(HERE)} : {m.taille[0]:.1f} × {m.taille[1]:.1f} × {m.taille[2]:.1f} mm, "
          f"{len(m.T)} triangles, {vol / 1000:.2f} cm³, version {info['version']}"
          f"{' + modifications non enregistrées' if info['non_enregistre'] else ''}")


if __name__ == "__main__":
    main()
