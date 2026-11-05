# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""3MF prêt à imprimer de la visière de l'afficheur, à partir du STL de scripts/export_visiere.py.

Usage : uv run visiere_3mf.py [dossier d'export]
  (défaut : le Temp Windows, %TEMP%/claudemetre/export)
  → print/visiere.3mf : projet Snapmaker Orca, PETG kaki (gabarit u1-petg, filament 4), debout sur son
    chant arrière, sans support ni bordure, au centre du plateau de la U1.

Le chant arrière, côté plateau, entre dans la rainure de la platine avec 0,1 mm de jeu par côté : pas
de bordure, et la compensation de pied d'éléphant du gabarit reste active.

Contrôles : maillage fermé, volume égal à celui du corps Fusion (à la tessellation près),
dimensions égales à celles de la visière, aucune face vers le bas hors du plateau (donc pas de support).
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
FILAMENT = 4                                # tête du PETG kaki, comme dans la coque enregistrée dans Orca
KAKI = "#547117"


def controle(m, info):
    tri = m.V[m.T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if abs(vol - info["volume"]) > 0.01 * info["volume"]:
        raise SystemExit(f"volume {vol:.1f} mm³ au lieu de {info['volume']}")
    e = np.sort(m.T[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    if (np.unique(e, axis=0, return_counts=True)[1] != 2).any():
        raise SystemExit("maillage ouvert")
    attendu = np.array([info["visiere_L"], info["visiere_dz_haut"] + info["visiere_dz_bas"],
                        info["visiere_P"] + info["rainure_p"]])
    if np.abs(m.taille - attendu).max() > 0.01:
        raise SystemExit(f"dimensions {m.taille} au lieu de {attendu}")
    bas = n[:, 2] < -1e-6 * np.linalg.norm(n, axis=1)
    if tri[bas][:, :, 2].max() > 1e-3:
        raise SystemExit(f"face vers le bas à z = {tri[bas][:, :, 2].max():.2f} : il faudrait un support")
    return vol, np.linalg.norm(n[bas], axis=1).sum() / 2


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    info = json.loads((src / "visiere.json").read_text(encoding="utf-8"))
    brut = maillage.lire_stl(src / "visiere.stl")
    # Rotation autour de X (pas de miroir) : le chant arrière (y maxi) passe sur le plateau, le toit à +Y.
    m = maillage.Maillage(np.c_[brut.V[:, 0], brut.V[:, 2], -brut.V[:, 1]], brut.T)
    m = m.deplace([-m.centre[0], -m.centre[1], -m.mini[2]])
    vol, appui = controle(m, info)

    projet = threemf.Projet(gabarit.charger(GABARIT).filaments([None, None, None, (KAKI, None, None)]))
    objet = projet.objet("visiere", filament=FILAMENT)
    objet.piece(m, "visiere")
    projet.placer(objet)
    sortie = HERE / "print" / "visiere.3mf"
    projet.ecrire(sortie)
    print(f"{sortie.relative_to(HERE)} : {m.taille[0]:.1f} × {m.taille[1]:.1f} × {m.taille[2]:.1f} mm, "
          f"{len(m.T)} triangles, {vol / 1000:.2f} cm³, appui {appui:.0f} mm², version {info['version']}"
          f"{' + modifications non enregistrées' if info['non_enregistre'] else ''}")
    for niveau, message in threemf.verifier(sortie):
        print(niveau, message)


if __name__ == "__main__":
    main()
