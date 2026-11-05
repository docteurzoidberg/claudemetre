# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "shapely>=2.0", "fonttools", "ezdxf"]
# ///
"""Textes des plaquettes SESSION / SEMAINE / RÉINIT., en contours pour Fusion 360.

Même rendu que les cadrans (fonctions de design/dials/so45_print.py) :
Barlow Semi Condensed Medium, capitales de CAP mm, centrées sur la plaquette.
Les cotes viennent du tranchage de vraies plaquettes (Snapmaker
Orca, Arachne, lignes de 0,42), pas du seul dessin.

Usage : uv run plaquettes_texte.py
  → dxf/<mot>.dxf : contours fermés en mm, origine au centre de la plaquette,
    x vers la droite, y vers le haut (vue de face) ;
  → dxf/<mot>_flip.dxf : le même, retourné haut-bas (l'import dans Fusion sur un
    plan parallèle à XZ inverse l'axe vertical) ;
  → dxf/plaquettes.json : pour chaque mot, l'aire et le centre de chaque
    polygone d'encre (sert à reconnaître les profils dans Fusion).
"""
import json
import sys
from pathlib import Path

import ezdxf
from shapely import affinity
from shapely.geometry import Point
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "dials"))
import so45_print as sp  # noqa: E402

sp._min_stroke.__defaults__ = (0.0,)   # pas d'épaississement lettre par lettre : BOLD, uniforme, s'en charge

FONT = "BarlowSemiCondensed-Medium.ttf"
CAP = 3.0            # hauteur de capitale (mm) ; le mot le plus large fait alors 17,4 mm (23 au plus entre les vis)
TRACK = 0.14         # interlettrage, en fraction de la hauteur de capitale
BOLD = 0.062         # épaississement par côté : barre du E à 0,48 mm, fût à 0,54 (à 0,46, le tranchage perd des coins du M)
DOT_D = 0.9          # point dessiné à part, comme sur les cadrans : celui de la police (0,7 mm au mieux) saute au tranchage
DOT_GAP = 0.45       # entre le T et le point, plus la moitié de l'interlettrage
WORDS = {"session": "SESSION", "semaine": "SEMAINE", "reinit": "RÉINIT."}
OUT = HERE / "dxf"


def cap_ratio():
    f = sp._font(FONT, None)
    gs, cm = f.getGlyphSet(), f.getBestCmap()
    pen = sp._Flatten(gs)
    gs[cm[ord("H")]].draw(pen)
    ys = [y for c in pen.contours for _, y in c]
    return (max(ys) - min(ys)) / f["head"].unitsPerEm


def word_shape(word, size):
    """Mot centré sur la plaquette, y = 0 à mi-hauteur des capitales. Le point final est un vrai disque."""
    dot = word.endswith(".")
    g = sp.text_shape(word.rstrip("."), (FONT, None, size, BOLD), spacing=TRACK * CAP)
    x0, _, x1, _ = g.bounds
    g = affinity.translate(g, 0, -CAP / 2)
    if dot:
        d = Point(x1 + DOT_GAP + TRACK * CAP / 2 + DOT_D / 2, -CAP / 2 + DOT_D / 2).buffer(DOT_D / 2, 24)
        g = unary_union([g, d])
    x0, _, x1, _ = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, 0), x1 - x0


def write_dxf(g, path):
    doc = ezdxf.new("R2010", setup=False)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for p in sp._polys(g):
        for ring in (p.exterior, *p.interiors):
            msp.add_lwpolyline([(x, y) for x, y in list(ring.coords)[:-1]], close=True)
    doc.saveas(path)


def main():
    OUT.mkdir(exist_ok=True)
    size = CAP / cap_ratio()
    index = {}
    for key, word in WORDS.items():
        g, width = word_shape(word, size)
        write_dxf(g, OUT / f"{key}.dxf")
        write_dxf(affinity.scale(g, 1, -1, origin=(0, 0)), OUT / f"{key}_flip.dxf")
        polys = []
        for p in sp._polys(g):
            c = p.centroid
            polys.append({"area": round(p.area, 4), "cx": round(c.x, 3), "cy": round(c.y, 3)})
        index[key] = {"word": word, "width": round(width, 2), "polys": polys,
                      "thin": round(sp.thin_parts(g).area, 3)}
        print(f"{word:8s} largeur {width:5.2f} mm, {len(polys)} polygones, trait trop fin {index[key]['thin']} mm²")
    (OUT / "plaquettes.json").write_text(json.dumps({"font": FONT, "cap": CAP, "track": TRACK, "bold": BOLD,
                                                     "dot": DOT_D, "words": index},
                                                    ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
