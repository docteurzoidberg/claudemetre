# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "shapely>=2.0", "fonttools", "ezdxf"]
# ///
"""Tracés SVG de la carte Lovelace, écrits dans claudemetre-card.js.

La carte reste un seul fichier JS sans build : ce script ne fait que
réécrire son bloc ASSETS (entre les marqueurs), à relancer quand les cadrans,
les plaquettes ou l'afficheur changent.

  - cadrans : mêmes géométries que les appliques imprimées
    (design/dials/so45_print.py, style « dark ») ;
  - plaquettes : mêmes textes que les DXF de Fusion
    (design/plaquettes/plaquettes_texte.py) ;
  - voyant : légende CLAUDE, à recaler sur le témoin de l'objet ;
  - afficheur : contours exacts des segments du TM1637
    (design/references/tm1637/tm1637_segments.json) ;
  - glyphes des valeurs en % (sous les plaquettes) : même police et même
    hauteur de capitale que les plaquettes.

Tout est en mm, y vers le bas (repère SVG) : origine au centre de la fenêtre
du cadran, de la plaquette ou de l'afficheur.

Usage : uv run card_assets.py
"""
import json
import re
import sys
from pathlib import Path

from shapely import affinity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CARD = ROOT / "homeassistant" / "www" / "claudemetre" / "claudemetre-card.js"
sys.path.insert(0, str(ROOT / "design" / "dials"))
sys.path.insert(0, str(ROOT / "design" / "plaquettes"))
import so45_print as sp  # noqa: E402
import plaquettes_texte as pt  # noqa: E402

BEGIN, END = "// >>> card_assets.py", "// <<< card_assets.py"
STYLE = "dark"
LAMP = {"word": "CLAUDE", "size": 6.2, "spacing": 1.15}  # corps et interlettrage (facteur Blender) de la maquette


def num(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def ring_d(coords):
    pts = [(x, -y) for x, y in coords]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    head = f"M{num(pts[0][0])} {num(pts[0][1])}"
    return head + "".join(f"L{num(x)} {num(y)}" for x, y in pts[1:]) + "Z"


def path_d(g, tol=0.02):
    """Polygones shapely (y vers le haut) → chemin SVG (y vers le bas), à
    remplir en evenodd. Tolérance de 0,02 mm : invisible même en plein écran."""
    g = g.simplify(tol)
    return "".join(ring_d(r.coords) for p in sp._polys(g) for r in (p.exterior, *p.interiors))


def dot_d(pts):
    """Point rond (deux-points, point décimal) : un cercle, plutôt que ses 52 sommets."""
    xs, ys = [x for x, _ in pts], [-y for _, y in pts]
    cx, cy, r = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (max(xs) - min(xs)) / 2
    return f"M{num(cx - r)} {num(cy)}A{num(r)} {num(r)} 0 1 0 {num(cx + r)} {num(cy)}A{num(r)} {num(r)} 0 1 0 {num(cx - r)} {num(cy)}Z"


def dials():
    st = sp.STYLES[STYLE]
    bodies = {key: sp.dial(sub, st) for key, sub in sp.DIALS}
    s = bodies["session"]
    return {
        "spec": {k: sp.SPEC[k] for k in ("window_r", "chord_z", "pivot_z", "arc_r", "sweep_deg", "needle_len")},
        "rgb": {k: "#%02x%02x%02x" % v for k, v in st["rgb"].items()},
        # L'échelle et la zone sont les mêmes sur les deux cadrans ; seul le texte change.
        "scale": path_d(s["echelle"]),
        "zone": path_d(s["zone"]),
        "text": {key: path_d(b["texte"]) for key, b in bodies.items()},
    }


def plaquettes():
    size = pt.CAP / pt.cap_ratio()
    out = {}
    for key, word in pt.WORDS.items():
        g = sp.text_shape(word, (pt.FONT, None, size, 0.0), spacing=pt.TRACK * pt.CAP)
        x0, _, x1, _ = g.bounds
        out[key] = path_d(affinity.translate(g, -(x0 + x1) / 2, -pt.CAP / 2))
    return out


def lamp():
    """Légende du voyant, centrée sur la hauteur de capitale."""
    f = sp._font(pt.FONT, None)
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    k = LAMP["size"] / f["head"].unitsPerEm
    advance = sum(gs[cmap[ord(ch)]].width for ch in LAMP["word"]) * k / len(LAMP["word"])
    g = sp.text_shape(LAMP["word"], (pt.FONT, None, LAMP["size"], 0.0), spacing=(LAMP["spacing"] - 1) * advance)
    cap = LAMP["size"] * pt.cap_ratio()
    x0, _, x1, _ = g.bounds
    return {"cap": round(cap, 3), "width": round(x1 - x0, 3), "d": path_d(affinity.translate(g, -(x0 + x1) / 2, -cap / 2))}


def glyphs():
    """Glyphes un par un (origine sur la ligne de base, à gauche) et leur chasse :
    la carte compose « 62 % » elle-même."""
    size = pt.CAP / pt.cap_ratio()
    f = sp._font(pt.FONT, None)
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    k = size / f["head"].unitsPerEm
    width = lambda ch: round(gs[cmap[ord(ch)]].width * k, 3)
    chars = {ch: {"d": path_d(sp.text_shape(ch, (pt.FONT, None, size, 0.0))), "w": width(ch)} for ch in "0123456789%-"}
    return {"cap": pt.CAP, "track": round(pt.TRACK * pt.CAP, 3), "space": width(" "), "chars": chars}


def segments():
    spec = json.loads((ROOT / "design" / "references" / "tm1637" / "tm1637_segments.json").read_text())
    return {
        "digits": [{s: ring_d(p) for s, p in d.items()} for d in spec["digits"]],
        "colon": "".join(dot_d(p) for p in spec["colon"]),
        "dp": "".join(dot_d(p) for p in spec["dp"]),
    }


def main():
    assets = {"dial": dials(), "plate": plaquettes(), "lamp": lamp(), "glyphs": glyphs(), "seg": segments()}
    block = (f"{BEGIN} (généré, ne pas modifier à la main)\n"
             f"const ASSETS = {json.dumps(assets, ensure_ascii=False, separators=(',', ':'))};\n{END}")
    js = CARD.read_text()
    new, n = re.subn(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: block, js, flags=re.S)
    assert n == 1, f"marqueurs introuvables dans {CARD}"
    CARD.write_text(new)
    print(f"{CARD.relative_to(ROOT)} : bloc ASSETS de {len(block) / 1024:.1f} Ko, fichier de {len(new) / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
