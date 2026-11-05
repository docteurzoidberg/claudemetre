# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "matplotlib"]
# ///
"""3MF prêts à imprimer des cadrans fond-jauge-session et fond-jauge-semaine,
à partir des STL exportés de Fusion par scripts/export_cadrans.py.

Usage : uv run cadran_3mf.py [dossier d'export]
  (défaut : le Temp Windows, %TEMP%/claudemetre/export)
  → print/<variante>.3mf : projet Snapmaker Orca, un objet à 4 pièces, une
    par couleur (fond, echelle, zone, texte), face visible contre le plateau,
    au centre du plateau de la U1. Réglages : gabarit `u1-4pla-cadrans` de la
    bibliothèque commune impression-3d (~/3d/impression-3d/gabarits, le profil
    U1 de l'utilisateur), sauf les réglages
    d'impression du cadran (REGLAGES). Écriture du 3MF par imp3d.threemf
    (skill impression-3d) : sans bloc <plate>, il se tranche en ligne de
    commande (imp3d tranche).
    Aucune pièce n'est attribuée à un filament : filaments et têtes se
    choisissent au moment d'imprimer. Un 3MF inscrit à FICHIERS_VALIDES.md
    (verrouillé : ré-enregistré par l'utilisateur) n'est pas réécrit : la
    nouvelle version va dans %TEMP%/claudemetre/valides_nouveaux ;
  → print/<variante>_apercu.png : la face vue sous le plateau, aux couleurs
    des apparences Fusion.

Contrôles : maillages fermés et orientés, volume égal à celui des corps
Fusion (à la tessellation près), couleurs à fleur de la face.
"""
import json
import sys
from pathlib import Path

from prive import WIN_TEMP

import numpy as np

sys.path.insert(0, str(Path.home() / "3d/impression-3d"))
from imp3d import gabarit as imp3d_gabarit, maillage as imp3d_maillage, threemf as imp3d_threemf  # noqa: E402
from imp3d import valides as imp3d_valides  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = WIN_TEMP / "claudemetre/export"
OUT = HERE / "print"
# fichiers verrouillés (FICHIERS_VALIDES.md d'ici, imp3d.valides) : jamais réécrits, nouvelle version mise à part
A_PART = WIN_TEMP / "claudemetre/valides_nouveaux"
GABARIT = "u1-4pla-cadrans"     # imp3d gabarits
# Hauteur et largeur de la première couche sont des réglages globaux (pas par
# objet) : d'où un projet complet plutôt que des réglages d'objet.
REGLAGES = {
    "layer_height": "0.2",
    "initial_layer_print_height": "0.2",      # 4 couches de couleur, face à 0,8 des piliers
    "initial_layer_line_width": "0.42",       # traits de 0,5 mm non empâtés
    "initial_layer_speed": "30",              # première couche lente (par extrudeur)
    "initial_layer_infill_speed": "60",
    "wall_generator": "arachne",              # traits fins en une ligne de largeur variable
    "sparse_infill_density": "100%",
    "enable_prime_tower": "1",
}
STL = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])

def read_stl(path):
    """Triangles d'un STL binaire, sommets fusionnés (Fusion écrit le même
    sommet à l'identique dans chaque triangle)."""
    data = path.read_bytes()
    n = int.from_bytes(data[80:84], "little")
    tri = np.frombuffer(data, STL, n, 84)["v"].reshape(-1, 3).astype(np.float64)
    verts, idx = np.unique(tri, axis=0, return_inverse=True)
    faces = idx.reshape(-1, 3)
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    return verts, faces[keep]


def check(name, verts, faces, volume_ref):
    """Maillage fermé et orienté : chaque arête parcourue autant de fois dans
    un sens que dans l'autre. Une arête vue par 4 triangles est admise : deux
    logements de couleur s'y touchent (zone au bout d'une graduation), le fond
    y a une épaisseur nulle, ce dont le trancheur s'accommode. Volume conforme
    au corps Fusion. Renvoie le nombre de ces arêtes de contact."""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    n = len(verts)
    keys, counts = np.unique(e[:, 0] * n + e[:, 1], return_counts=True)
    rev = (keys % n) * n + keys // n
    pos = np.minimum(np.searchsorted(keys, rev), len(keys) - 1)
    bad = (keys[pos] != rev) | (counts[pos] != counts)
    if bad.any():
        raise SystemExit(f"{name} : maillage ouvert ou mal orienté ({bad.sum()} arêtes sans retour)")
    a, b, c = (verts[faces[:, k]] for k in range(3))
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6
    if abs(vol - volume_ref) > 0.01 * volume_ref:
        raise SystemExit(f"{name} : volume {vol:.2f} mm³ au lieu de {volume_ref} (unités ?)")
    return int((np.unique(np.sort(e, axis=1), axis=0, return_counts=True)[1] > 2).sum())


def project_settings():
    """Gabarit U1 et réglages du cadran."""
    return imp3d_gabarit.charger(GABARIT).regler(REGLAGES)


def apercu(path, name, parts, rgb):
    """Triangles posés sur le plateau, vus de dessous : la face imprimée."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    fig, ax = plt.subplots(figsize=(5, 5))
    for comp, verts, faces in parts:                    # fond d'abord, couleurs par-dessus
        tri = verts[faces]
        tri = tri[(tri[:, :, 2] < 1e-4).all(1)][:, :, :2] * (-1, 1)
        color = np.array(rgb[comp]) / 255 if rgb[comp] else "0.5"
        ax.add_collection(PolyCollection(tri, facecolors=color, edgecolors=color, linewidths=0.1))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{name} : face vue sous le plateau", fontsize=9)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="0.6")
    plt.close(fig)


def build(name, src, comps):
    parts, contacts = [], {}
    for comp, info in sorted(comps.items(), key=lambda c: c[0] != "fond"):    # fond d'abord
        verts, faces = read_stl(src / f"{comp}.stl")
        n = check(f"{name}/{comp}", verts, faces, info["volume"])
        parts.append([comp, verts * (-1, 1, -1), faces])        # retourné autour de Y : face au plateau
        if n:
            contacts[comp] = n
    fond = next(v for c, v, f in parts if c == "fond")
    shift = -np.array([*(fond.min(0)[:2] + fond.max(0)[:2]) / 2, fond.min(0)[2]])
    log = []
    for p in parts:
        p[1] = p[1] + shift
        z0 = p[1][:, 2].min()
        if abs(z0) > 1e-3:
            raise SystemExit(f"{name}/{p[0]} : pas à fleur de la face (z min {z0:.3f} mm)")
        size = p[1].max(0) - p[1].min(0)
        rgb = comps[p[0]].get("rgb")
        log.append(f"  {p[0]:8s} {'#%02X%02X%02X' % tuple(rgb) if rgb else '?':8s} {len(p[2]):6d} triangles, "
                   f"{size[0]:5.1f} × {size[1]:5.1f} × {size[2]:4.2f} mm")
    w, h, e = (fond + shift).max(0) - (fond + shift).min(0)
    if not 30 < w < 60:
        raise SystemExit(f"{name} : cadran de {w:.1f} mm de large (unités ?)")
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.3mf"
    try:
        rel = path.resolve().relative_to(HERE).as_posix()
    except ValueError:
        rel = None
    etat = imp3d_valides.etat(HERE, rel) if rel else None
    if etat:          # verrouillé (ré-enregistré par l'utilisateur avec ses filaments, ou validé)
        A_PART.mkdir(parents=True, exist_ok=True)
        print(f"VALIDE GARDE : {rel} verrouillé ({etat}), non réécrit ; nouvelle version dans {A_PART}")
        path = A_PART / path.name
    projet = imp3d_threemf.Projet(project_settings())
    objet = projet.objet(name)                        # ni filament ni tête : choisis à l'impression
    for comp, verts, faces in parts:
        objet.piece(imp3d_maillage.Maillage(verts, faces), comp)
    projet.placer(objet)                              # centre du plateau de la U1
    projet.ecrire(path)
    apercu(path.with_name(f"{name}_apercu.png"), name, parts, {c: i.get("rgb") for c, i in comps.items()})
    print(f"{path.relative_to(HERE) if path.is_relative_to(HERE) else path} : 1 objet, {len(parts)} pièces, "
          f"{w:.1f} × {h:.1f} × {e:.2f} mm")
    print("\n".join(log))
    for comp, n in contacts.items():
        print(f"  {comp} : {n} arêtes de contact entre logements (épaisseur nulle, admis)")


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    manifest = json.loads((src / "export.json").read_text(encoding="utf-8"))
    for a in manifest.pop("avertissements"):
        print("ATTENTION :", a)
    for name, m in manifest.items():
        build(name, src / name, m["composants"])


if __name__ == "__main__":
    main()
