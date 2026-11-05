# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["cadquery-ocp", "numpy", "shapely>=2.0"]
# ///
"""Extrait du STEP GrabCAD du module TM1637 0,56" le contour de ses segments.

Usage : uv run step_to_segments.py
  → tm1637_segments.json : contour exact des 28 segments, des 4 points
    décimaux et du deux-points, pour les allumer selon l'heure affichée.
    Origine au centre de la face avant de l'afficheur, Z vers le haut, en mm.

Dans le STEP (CATIA, mm), la face avant est en z = 0 et le module s'étend
vers -z ; les segments sont des alvéoles vertes de 0,08 mm dans la face.
Le sérigraphie (solides d'épaisseur nulle) et la plaque interne de
l'afficheur sont ignorées.
"""
import json
import re
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.IFSelect import IFSelect_RetDone
from OCP.Quantity import Quantity_Color
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
STEP = HERE / "Display_4-Didi_LED_TM1637.stp"
GREEN = (0.0, 1.0, 0.0)


def bbox(s):
    b = Bnd_Box()
    BRepBndLib.Add_s(s, b, False)
    p, q = b.CornerMin(), b.CornerMax()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def explore(s, kind):
    e = TopExp_Explorer(s, kind)
    while e.More():
        yield e.Current()
        e.Next()


def part(colour, size):
    """Matière d'un solide d'après sa couleur STEP et ses dimensions."""
    if size.min() < 0.01 or np.allclose(size, (49.2, 18.0, 0.8), atol=0.1):
        return None                       # sérigraphie, plaque interne de l'afficheur
    if np.allclose(size, (66.0, 27.2, 1.6), atol=0.1):
        return "pcb"
    if np.allclose(size, (50.2, 19.0, 7.9), atol=0.1):
        return "corps"
    if np.allclose(size, (50.2, 19.0, 0.1), atol=0.05):
        return "face"
    if colour is not None and max(colour) < 0.15:
        return "noir"                     # TM1637, connecteur, résistances
    if colour == (0.65, 0.45, 0.21):
        return "composants"               # condensateurs
    return "metal"                        # broches, soudures, pastilles


def triangles(s):
    """Triangles du solide maillé, repère cm_lib : (x, y, z)_STEP → (x, -z, y)."""
    tris = []
    for f in explore(s, TopAbs_FACE):
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(TopoDS.Face(f), loc)
        if tri is None:
            continue
        tr = loc.Transformation()
        nodes = []
        for k in range(1, tri.NbNodes() + 1):
            p = tri.Node(k).Transformed(tr)
            nodes.append((p.X(), -p.Z(), p.Y()))
        rev = f.Orientation() == TopAbs_REVERSED
        for k in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(k).Get()
            tris.append([nodes[a - 1], nodes[c - 1], nodes[b - 1]] if rev else [nodes[a - 1], nodes[b - 1], nodes[c - 1]])
    return tris


def outline(face):
    """Contour d'une face plane (union de ses triangles), en (x, z) cm_lib =
    (x, y) STEP."""
    tris = [Polygon([(x, z) for x, _, z in t]) for t in triangles(face)]
    poly = unary_union([t.buffer(1e-4) for t in tris if t.area > 0]).buffer(-1e-4)
    return orient(poly.simplify(0.002), 1.0)


def name_segments(polys):
    """28 segments → 4 chiffres (gauche à droite) × a-g ; ronds → dp, deux-points."""
    round_ = [p for p in polys if p.area < 2.0 and abs(p.bounds[2] - p.bounds[0] - (p.bounds[3] - p.bounds[1])) < 0.1]
    bars = [p for p in polys if p not in round_]
    assert len(bars) == 28 and len(round_) == 6, (len(bars), len(round_))
    colon = sorted((p for p in round_ if abs(p.centroid.x) < 1.0), key=lambda p: -p.centroid.y)
    dp = sorted((p for p in round_ if abs(p.centroid.x) >= 1.0), key=lambda p: p.centroid.x)
    bars.sort(key=lambda p: p.centroid.x)
    # Les chiffres se chevauchent en x à cause de l'italique : regroupement par
    # le centre des barres horizontales, les plus nettes.
    digits = []
    horiz = sorted((p for p in bars if p.bounds[2] - p.bounds[0] > p.bounds[3] - p.bounds[1]), key=lambda p: p.centroid.x)
    centres = [np.mean([p.centroid.x for p in horiz[k * 3:k * 3 + 3]]) for k in range(4)]
    groups = [[] for _ in range(4)]
    for p in bars:
        groups[int(np.argmin([abs(p.centroid.x - c) for c in centres]))].append(p)
    for g in groups:
        assert len(g) == 7, len(g)
        h = sorted((p for p in g if p.bounds[2] - p.bounds[0] > p.bounds[3] - p.bounds[1]), key=lambda p: -p.centroid.y)
        v = sorted((p for p in g if p not in h), key=lambda p: -p.centroid.y)
        top, bottom = sorted(v[:2], key=lambda p: p.centroid.x), sorted(v[2:], key=lambda p: p.centroid.x)
        digits.append(dict(zip("agdfbec", h + top + bottom)))
    return digits, dp, colon


def coords(p):
    return [[round(x, 3), round(y, 3)] for x, y in p.exterior.coords[:-1]]


def main():
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader()
    r.SetColorMode(True)
    assert r.ReadFile(str(STEP)) == IFSelect_RetDone
    r.Transfer(doc)
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    shape = r.Reader().OneShape()
    BRepMesh_IncrementalMesh(shape, 0.02, False, 0.25, True)

    def colour(s):
        c = Quantity_Color()
        for t in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
            if ct.GetColor(s, t, c):
                return round(c.Red(), 2), round(c.Green(), 2), round(c.Blue(), 2)
        return None

    holes = []
    for s in explore(shape, TopAbs_SOLID):
        lo, hi = bbox(s)
        if part(colour(s), hi - lo) == "face":
            for f in explore(s, TopAbs_FACE):
                flo, fhi = bbox(f)
                if colour(f) == GREEN and abs(flo[2] + 0.08) < 1e-3 and abs(fhi[2] + 0.08) < 1e-3:
                    holes.append(outline(f))
    digits, dp, colon = name_segments(holes)
    spec = {
        "source": STEP.name,
        "notes": "mm, origine au centre de la face avant de l'afficheur, x à droite, z vers le haut ; "
                 "polygones dans le sens trigonométrique, au fond d'alvéoles de profondeur depth",
        "depth": 0.08,
        "digits": [{k: coords(p) for k, p in sorted(d.items())} for d in digits],
        "dp": [coords(p) for p in dp],
        "colon": [coords(p) for p in colon],
    }
    text = json.dumps(spec, indent=1, ensure_ascii=False)
    text = re.sub(r"\[\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]", r"[\1, \2]", text)    # un point par ligne
    (HERE / "tm1637_segments.json").write_text(text)
    hs = [d["a"] for d in digits]
    print("chiffres, centre du segment a :", [round(p.centroid.x, 2) for p in hs],
          "hauteur a→d :", round(digits[0]["a"].bounds[3] - digits[0]["d"].bounds[1], 2), "mm")


if __name__ == "__main__":
    main()
