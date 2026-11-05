# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "shapely>=2.0", "fonttools", "ezdxf"]
# ///
"""Contours d'un cadran imprimable en DXF, pour l'incruster dans le design
Fusion `fond-jauge` (scripts/fond_jauge.py, fonction incrustation).

Usage : uv run cadran_dxf.py [style] [session|semaine]     (dark session par défaut)
  → cadran_dxf/<corps>.dxf : contours fermés en mm, origine au centre de la
    plaque, y vers le haut (echelle, zone, texte) ;
  → cadran_dxf/cadran.json : aire et centre de chaque polygone, pour que le
    script Fusion retrouve les profils à incruster (pas les contre-formes).
"""
import json
import sys
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "dials"))
import so45_print as sp  # noqa: E402

OUT = HERE / "cadran_dxf"


def main():
    style = sys.argv[1] if len(sys.argv) > 1 else "dark"
    key = sys.argv[2] if len(sys.argv) > 2 else "session"
    st = sp.STYLES[style]
    bodies = sp.dial(dict(sp.DIALS)[key], st)
    OUT.mkdir(exist_ok=True)
    index = {"style": style, "dial": key, "rgb": st["rgb"], "bodies": {}}
    for name in sp.BODIES[1:]:
        # Ouverture de 1 µm : sépare les morceaux qui se touchent en un point
        # (zone coupée pile au bout des petits traits), sinon Fusion découpe
        # le contour en profils qui ne correspondent plus aux polygones.
        bodies[name] = bodies[name].buffer(-1e-3, join_style="mitre").buffer(1e-3, join_style="mitre")
        doc = ezdxf.new("R2010", setup=False)
        doc.units = ezdxf.units.MM
        msp = doc.modelspace()
        polys = []
        for p in sp._polys(bodies[name]):
            for ring in (p.exterior, *p.interiors):
                msp.add_lwpolyline([(x, y) for x, y in list(ring.coords)[:-1]], close=True)
            c = p.centroid
            polys.append({"area": round(p.area, 4), "cx": round(c.x, 3), "cy": round(c.y, 3)})
        doc.saveas(OUT / f"{name}.dxf")
        index["bodies"][name] = polys
        print(f"{name:8s} {len(polys):3d} polygones, {bodies[name].area:7.2f} mm²")
    (OUT / "cadran.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
