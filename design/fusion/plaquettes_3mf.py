# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""3MF prêt à imprimer des trois plaquettes, à partir des STL de scripts/export_plaquettes.py.

Usage : uv run plaquettes_3mf.py [dossier d'export]
  (défaut : le Temp Windows, %TEMP%/claudemetre/export/plaquettes)
  → print/plaquettes.3mf : projet Snapmaker Orca, PLA (gabarit u1-4pla), trois objets à deux pièces,
    `noir` (filament 4) et `blanc` (filament 1), face visible sur le plateau.

Les réglages sont ceux du tranchage qui a fixé la police et le trait (couches de 0,2 dès la première,
lignes de 0,42, Arachne) : sans eux, les traits de 0,5 mm ne sortent pas de la même façon.

Contrôles : maillages fermés, volume égal à celui des corps Fusion, cotes de la plaquette, texte à fleur
de la face et incrusté de `texte_p`.
"""
import json
import sys
from pathlib import Path

from prive import WIN_TEMP

import numpy as np

sys.path.insert(0, str(Path.home() / "3d/impression-3d"))
from imp3d import gabarit, maillage, threemf  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = WIN_TEMP / "claudemetre/export/plaquettes"
GABARIT = "u1-4pla"
BLANC, NOIR = 1, 4                          # T1 blanc, T4 noir dans le gabarit
PAS_Y = 16                                  # entre deux plaquettes sur le plateau
REGLAGES = {
    "layer_height": "0.2",
    "initial_layer_print_height": "0.2",    # 3 couches de texte sur texte_p = 0,6
    "initial_layer_line_width": "0.42",     # traits de 0,5 mm non empâtés
    "initial_layer_speed": "30",
    "initial_layer_infill_speed": "60",
    "wall_generator": "arachne",            # traits fins en une ligne de largeur variable
    "sparse_infill_density": "100%",
    "enable_prime_tower": "1",
}


def volume(m):
    tri = m.V[m.T]
    return np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6


def lire(src, row):
    """Corps Fusion → repère d'impression : rotation autour de X (pas de miroir), face visible (y mini) vers le bas."""
    m = maillage.lire_stl(src / row["stl"])
    e = np.sort(m.T[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    if (np.unique(e, axis=0, return_counts=True)[1] != 2).any():
        raise SystemExit(f"{row['stl']} : maillage ouvert")
    if abs(volume(m) - row["volume"]) > 0.01 * row["volume"]:
        raise SystemExit(f"{row['stl']} : volume {volume(m):.2f} mm³ au lieu de {row['volume']}")
    return maillage.Maillage(np.c_[m.V[:, 0], -m.V[:, 2], m.V[:, 1]], m.T)


def fusionner(ms):
    n = np.cumsum([0] + [len(m.V) for m in ms])
    return maillage.Maillage(np.vstack([m.V for m in ms]), np.vstack([m.T + k for m, k in zip(ms, n)]))


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    info = json.loads((src / "export.json").read_text(encoding="utf-8"))
    projet = threemf.Projet(gabarit.charger(GABARIT).regler(REGLAGES))
    cx, cy = projet.gabarit.centre()
    for i, (key, e) in enumerate(info["plaquettes"].items()):
        noir = lire(src, e["noir"])
        blanc = fusionner([lire(src, r) for r in e["blanc"]])
        d = -np.array([*noir.centre[:2], noir.mini[2]])
        noir, blanc = noir.deplace(d), blanc.deplace(d)
        attendu = np.array([info["plaq_L"], info["plaq_H"], info["plaq_ep"]])
        if np.abs(noir.taille - attendu).max() > 0.01:
            raise SystemExit(f"{key} : {noir.taille} au lieu de {attendu}")
        if abs(blanc.mini[2]) > 1e-3 or abs(blanc.maxi[2] - info["texte_p"]) > 1e-3:
            raise SystemExit(f"{key} : texte de z {blanc.mini[2]:.3f} à {blanc.maxi[2]:.3f}")
        objet = projet.objet("plaquette_" + key)
        objet.piece(noir, "noir", filament=NOIR)
        objet.piece(blanc, "blanc", filament=BLANC)
        projet.placer(objet, position=(cx, cy + (1 - i) * PAS_Y))
        print(f"{key:8s} {noir.taille[0]:.1f} × {noir.taille[1]:.1f} × {noir.taille[2]:.2f} mm, "
              f"{len(e['blanc'])} morceaux de texte, largeur {blanc.taille[0]:.2f} mm")
    sortie = HERE / "print" / "plaquettes.3mf"
    projet.ecrire(sortie)
    print(f"{sortie.relative_to(HERE)}, version {info['version']}"
          f"{' + modifications non enregistrées' if info['non_enregistre'] else ''}")
    for niveau, message in threemf.verifier(sortie):
        print(niveau, message)


if __name__ == "__main__":
    main()
