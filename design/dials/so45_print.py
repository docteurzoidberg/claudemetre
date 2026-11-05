# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "shapely>=2.0", "fonttools"]
# ///
"""Cadrans SO-45 imprimables en 3D multi-filament (Snapmaker U1, 4 têtes).

Le cadran reprend la forme exacte de la plaque d'origine (découpe centrale
et trous de vis compris) et la remplace, vissé sur les deux piliers avec les
mêmes vis. Il est imprimé face visible contre le plateau. Chaque couleur est
un corps séparé, sur une profondeur `color` depuis la face (mosaïque), si
bien qu'une couleur claire n'est jamais posée en couche mince sur un fond
sombre. Derrière, le fond remplit la plaque jusqu'à `total` et la rigidifie,
sauf autour des trous : des lamages y laissent passer les piliers. La face
est donc à `seat` au-dessus des piliers, réglable seul (aiguille penchée :
c'est près de l'axe que le jeu est le plus faible).

Usage : uv run so45_print.py
  → contrôle les cadrans : corps sans chevauchement, détails plus fins que la buse.

Les pièces à imprimer viennent de Fusion : design/fusion/cadran_dxf.py reprend
ces formes, puis le skill cadrans-3mf écrit design/fusion/print/fond-jauge-*.3mf.

Les cotes viennent de dial_so45_spec.json : plaque, axe et débattement
mesurés sur le cadran démonté ; reste le jeu sous l'aiguille (épaisseur).
"""
import json
import math
from pathlib import Path

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import polylabel, unary_union
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "fonts"
SPEC = json.loads((HERE / "dial_so45_spec.json").read_text())
PR = SPEC["print"]
PL = SPEC["plate"]

# Échelle, en mm. Avec une buse de 0,4, rien de plus fin que ~0,45 mm.
ARC_W = 0.6                     # arc principal
ZONE_W = 1.2                    # bande 80-100 %, sous l'arc
TICKS = {"major": (3.4, 0.8), "minor": (1.8, 0.5)}   # (longueur, largeur), tous les 25 % (chiffrés) et 5 %
NUM_R = 5.8                     # centre des chiffres, sous l'arc
NUM_SP = 0.25                   # espace ajouté entre chiffres (« 100 » trop serré sinon)
MIN_HOLE = 0.25                 # contre-forme plus petite (mm²) : bouchée, elle ne s'imprimerait pas
MIN_STROKE = 0.5                # morceau de texte plus fin : épaissi jusque-là (barre du %, 0,41 mm sinon)
SUB_Y = SPEC["pivot_z"] + SPEC["arc_r"] + 2.6   # « % · 5 H » au-dessus de l'arc ; le nom est sur la plaquette rivetée
DOT_D, DOT_GAP = 0.9, 1.0       # point du sous-titre, dessiné à part (celui de la police serait trop petit)
BODIES = ("fond", "echelle", "zone", "texte")

# Police : (fichier, graisse pour une police variable, corps en mm, épaississement en mm).
STYLES = {
    "dark": dict(
        rgb={"fond": (20, 20, 19), "echelle": (236, 234, 226), "zone": (226, 70, 30), "texte": (236, 234, 226)},
        num=("BarlowCondensed-SemiBold.ttf", None, 3.6, 0.05),
        sub=("BarlowCondensed-SemiBold.ttf", None, 3.4, 0.08)),
}
DIALS = (("session", "% · 5 H"), ("semaine", "% · 7 J"))


# ---------------------------------------------------------------- texte
_fonts = {}


def _font(file, wght):
    if (file, wght) not in _fonts:
        f = TTFont(FONTS / file)
        if wght is not None:
            f = instancer.instantiateVariableFont(f, {"wght": wght})
        _fonts[file, wght] = f
    return _fonts[file, wght]


class _Flatten(BasePen):
    """Contours de glyphe en polylignes (les quadratiques passent par
    _curveToOne, converties par BasePen)."""
    STEPS = 12

    def __init__(self, glyphset):
        super().__init__(glyphset)
        self.contours, self._pts = [], []

    def _moveTo(self, p):
        self._pts = [p]

    def _lineTo(self, p):
        self._pts.append(p)

    def _curveToOne(self, p1, p2, p3):
        x0, y0 = self._pts[-1]
        for k in range(1, self.STEPS + 1):
            t = k / self.STEPS
            u = 1 - t
            self._pts.append((u ** 3 * x0 + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                              u ** 3 * y0 + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))

    def _closePath(self):
        if len(self._pts) > 2:
            self.contours.append(self._pts)
        self._pts = []

    _endPath = _closePath


def text_shape(s, font, spacing=0.0):
    """Texte en polygones (mm), ligne de base en y = 0, règle pair-impair
    pour les trous des lettres."""
    file, wght, size, bold = font
    f = _font(file, wght)
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    k = size / f["head"].unitsPerEm
    x, parts = 0.0, []
    for ch in s:
        g = gs[cmap[ord(ch)]]
        pen = _Flatten(gs)
        g.draw(pen)
        shape = Polygon()
        for c in pen.contours:
            shape = shape.symmetric_difference(make_valid(Polygon(c)))
        parts.append(affinity.translate(affinity.scale(shape, k, k, origin=(0, 0)), x))
        x += g.width * k + spacing
    out = unary_union(parts)
    if bold:
        out = out.buffer(bold, join_style="mitre", mitre_limit=2.0)
    return unary_union([_min_stroke(Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= MIN_HOLE]))
                        for p in _polys(out)])


def _min_stroke(p, w=MIN_STROKE):
    """Morceau plus fin que w (diamètre du plus grand cercle inscrit) épaissi
    jusqu'à w : le trancheur abandonne une zone plus étroite qu'une ligne
    d'extrusion (en Classic, la barre du % en Barlow Condensed disparaissait)."""
    t = 2 * polylabel(p, 0.002).distance(p.boundary)
    return p.buffer((w - t) / 2, join_style="mitre", mitre_limit=2.0) if t < w else p


def centered(g, x, y):
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, x - (x0 + x1) / 2, y - (y0 + y1) / 2)


def sub_shape(s, font, y):
    """« % · 5 H » : deux morceaux de texte et un vrai point rond entre eux."""
    left, right = (text_shape(p.strip(), font, spacing=0.3) for p in s.split("·"))
    wl, wr = left.bounds[2] - left.bounds[0], right.bounds[2] - right.bounds[0]
    x = -(wl + wr + DOT_D + 2 * DOT_GAP) / 2
    dot = Point(x + wl + DOT_GAP + DOT_D / 2, y).buffer(DOT_D / 2, 32)
    return unary_union([centered(left, x + wl / 2, y), dot, centered(right, -x - wr / 2, y)])


# ---------------------------------------------------------------- cadran
def cutout():
    """Découpe centrale de la plaque d'origine, où passe l'équipage mobile :
    dôme, épaulements raccordés par des congés, flancs verticaux jusqu'en bas."""
    w, ys, rc = PL["slot_half"], PL["shoulder_z"], PL["fillet_r"]
    body = box(-w, -30, w, ys - rc).union(box(-w + rc, -30, w - rc, ys))
    for sx in (-1, 1):
        body = body.union(Point(sx * (w - rc), ys - rc).buffer(rc, 64))
    return body.union(Point(0, PL["dome_z"]).buffer(PL["dome_r"], 256))


def outline():
    """Contour de la plaque d'origine : disque, découpe centrale, trous de vis."""
    o = Point(0, 0).buffer(PL["radius"], 256).difference(cutout())
    for sx in (-1, 1):
        o = o.difference(Point(sx * PL["hole_x"], PL["hole_z"]).buffer(PL["hole_d"] / 2, 64))
    return o


def dial(sub, st):
    py, R, sw = SPEC["pivot_z"], SPEC["arc_r"], SPEC["sweep_deg"]

    def ang(v):
        return math.radians(-sw / 2 + sw * v / 100)

    def at(r, a):
        return r * math.sin(a), py + r * math.cos(a)

    def bar(r0, r1, a, w):
        nx, ny = math.cos(a) * w / 2, -math.sin(a) * w / 2
        (x0, y0), (x1, y1) = at(r0, a), at(r1, a)
        return Polygon([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)])

    def band(r0, r1, a0, a1, n=120):
        aa = np.linspace(a0, a1, n)
        return Polygon([at(r1, a) for a in aa] + [at(r0, a) for a in aa[::-1]])

    e = TICKS["major"][1] / 2 / R
    parts = [band(R - ARC_W, R, ang(0) - e, ang(100) + e)]
    for v in range(0, 101, 5):
        length, width = TICKS["major" if v % 25 == 0 else "minor"]
        parts.append(bar(R - length, R, ang(v), width))
    for v in range(0, 101, 25):
        parts.append(centered(text_shape(str(v), st["num"], spacing=NUM_SP), *at(R - NUM_R, ang(v))))
    o = outline()
    echelle = unary_union(parts).intersection(o)
    texte = sub_shape(sub, st["sub"], SUB_Y).intersection(o)
    zone = band(R - ARC_W - ZONE_W, R - ARC_W, ang(80), ang(100)).difference(echelle).intersection(o)
    fond = o.difference(echelle).difference(texte).difference(zone)
    return {"fond": fond, "echelle": echelle, "zone": zone, "texte": texte}


def thin_parts(g, w=PR["nozzle"]):
    """Détails plus fins que la buse : ce qui disparaît à l'ouverture
    morphologique de diamètre w. Les pointes des angles aigus, qui seront
    juste arrondies à l'impression, sont écartées (rognage de 0,06 mm puis
    seuil de 0,02 mm²)."""
    opened = g.buffer(-w / 2).buffer(w / 2)
    rest = g.difference(opened).buffer(-0.06)
    return unary_union([p for p in _polys(rest) if p.area > 0.02])


# ---------------------------------------------------------------- sorties
def _polys(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [p for p in getattr(g, "geoms", []) for p in _polys(p)]


def main():
    o_area = outline().area
    for name, st in STYLES.items():
        for key, sub in DIALS:
            bodies = dial(sub, st)
            total = sum(g.area for g in bodies.values())
            assert abs(total - o_area) < 1e-3, f"{name}/{key} : corps qui se chevauchent ou trous ({total} ≠ {o_area})"
            fine = [f"{b} {g.area:.3f} mm² vers ({g.centroid.x:.1f}, {g.centroid.y:.1f})"
                    for b, g in ((b, thin_parts(bodies[b])) for b in BODIES) if g.area > 0.005]
            print(f"{name:9s} {key:8s} détails < {PR['nozzle']} mm : {'; '.join(fine) or 'aucun'}")


if __name__ == "__main__":
    main()
