# Patron de perçage de la planche. Plaque mince aux dimensions de la coque, copie du dos
# du boîtier : ses trous tombent au centre des grands trous des fentes, là où passe la tête de vis.
# On le plaque sur la planche, on marque les deux trous. Le contour montre le boîtier au moment où
# on l'engage : il finit accroché accroche_course plus bas. Rangé derrière la coque dans l'assemblage.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('patron_ep', '0.6 mm', 'Patron : épaisseur'),
    ('patron_rail', '10 mm', 'Patron : largeur du cadre'),
    ('patron_barre', '20 mm', 'Patron : hauteur de la barre qui porte les trous'),
    ('patron_trou_d', '3 mm', 'Patron : diamètre des trous de marquage'),
    ('patron_z', 'accroche_z - accroche_jeu - accroche_course', 'Patron : hauteur des trous, au centre des grands trous des fentes'),
    ('patron_repere_l', '1.2 mm', 'Patron : largeur des encoches de repère'),
    ('patron_repere_p', '3 mm', 'Patron : profondeur des encoches de repère'),
    ('patron_y', 'coque_P + 5 mm', 'Patron : position de sa face plate dans l\'assemblage, derrière la coque'),
]


def is_corner_edge(e, L, H):
    g = e.geometry
    if not isinstance(g, adsk.core.Line3D):
        return False
    a, b = e.startVertex.geometry, e.endVertex.geometry
    if abs(a.x - b.x) > 1e-4 or abs(a.z - b.z) > 1e-4:
        return False
    return abs(abs(a.x) - L / 2) < 1e-3 and abs(abs(a.z) - H / 2) < 1e-3


def trous(comp, plan):
    """Deux cercles au centre des grands trous. Hauteur cotée depuis le haut de la coque : patron_z
    peut changer de signe, une cote depuis l'origine ne suivrait pas."""
    sk = sketch(comp, plan, 'patron_trous')
    H, x, z, r = ev('coque_H / 2'), ev('accroche_x'), ev('patron_z'), ev('patron_trou_d') / 2
    g, dm = sk.geometricConstraints, sk.sketchDimensions
    ref = sk.sketchPoints.add(spt(sk, 0, H))
    g.addVerticalPoints(sk.originPoint, ref)
    dm.addDistanceDimension(sk.originPoint, ref, VER, spt(sk, -0.5, H / 2)).parameter.expression = 'coque_H / 2'
    C = sk.sketchCurves.sketchCircles
    dr = C.addByCenterRadius(spt(sk, x, z), r)
    ga = C.addByCenterRadius(spt(sk, -x, z), r)
    dm.addDistanceDimension(sk.originPoint, dr.centerSketchPoint, HOR, spt(sk, x / 2, z + 1)).parameter.expression = 'accroche_x'
    dm.addDistanceDimension(sk.originPoint, ga.centerSketchPoint, HOR, spt(sk, -x / 2, z + 1)).parameter.expression = 'accroche_x'
    dm.addDistanceDimension(ref, dr.centerSketchPoint, VER, spt(sk, x + 1.2, H / 2)).parameter.expression = 'coque_H / 2 - patron_z'
    g.addHorizontalPoints(dr.centerSketchPoint, ga.centerSketchPoint)
    dm.addDiameterDimension(dr, spt(sk, x + r + 0.3, z + r + 0.3)).parameter.expression = 'patron_trou_d'
    g.addEqual(dr, ga)
    assert sk.profiles.count == 2, sk.profiles.count
    coll = adsk.core.ObjectCollection.create()
    for p in profiles(sk):
        coll.add(p)
    return coll


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    set_params(PARAMS)
    root = d.rootComponent
    coque = [o for o in root.occurrences if o.component.name == 'coque'][0].component.bRepBodies.item(0)
    occ = new_component('patron')
    comp = occ.component
    occ.activate()
    front = toward_front(comp)
    plan = plane_y(comp, 'patron_y', 'plan_patron')

    # Plaque aux dimensions de la coque.
    sk = sketch(comp, plan, 'patron_contour')
    centered_rect(sk, 'coque_L', 'coque_H')
    body = extrude(comp, sk.profiles.item(0), NEW, 'patron_ep', front, 'patron_plaque').bodies.item(0)
    body.name = 'patron'
    body.appearance = coque.appearance
    L, H = ev('coque_L'), ev('coque_H')
    fillet(comp, [e for e in body.edges if is_corner_edge(e, L, H)], 'coque_R', 'patron_coins')

    # Fenêtres : il reste le cadre et la barre, centrée sur les trous. Cotes depuis le cadre, toujours
    # positives ; le bord de la barre, lui, peut passer de part et d'autre de z = 0.
    w = 'coque_L - 2 * patron_rail'
    zc = 'coque_H / 2 - patron_rail'
    for name, h, s in (('haut', '%s - patron_z - patron_barre / 2' % zc, 1),
                       ('bas', '%s + patron_z - patron_barre / 2' % zc, -1)):
        sk = sketch(comp, plan, 'patron_fenetre_' + name)
        rect(sk, w, h, '( %s ) / 2' % w, zc, sx=-1, sz=s, cx=0, cz=s * (ev(zc) - ev(h) / 2))
        extrude(comp, sk.profiles.item(0), CUT, 'patron_ep', front, 'patron_coupe_' + name, [body])

    extrude(comp, trous(comp, plan), CUT, 'patron_ep', front, 'patron_trous_coupe', [body])

    # Encoches de repère aux milieux : le haut et la droite, puis miroirs.
    sk = sketch(comp, plan, 'patron_reperes')
    long_e, l_e = 'patron_repere_p + 1 mm', 'patron_repere_l'
    zt, xt = 'coque_H / 2 + 1 mm', 'coque_L / 2 + 1 mm'
    rect(sk, l_e, long_e, l_e + ' / 2', zt, sx=-1, sz=1, cx=0, cz=ev(zt) - ev(long_e) / 2)
    rect(sk, long_e, l_e, xt, l_e + ' / 2', sx=1, sz=-1, cx=ev(xt) - ev(long_e) / 2, cz=0)
    assert sk.profiles.count == 2, sk.profiles.count
    coll = adsk.core.ObjectCollection.create()
    for p in profiles(sk):
        coll.add(p)
    rep = extrude(comp, coll, CUT, 'patron_ep', front, 'patron_reperes_coupe', [body])
    mirror(comp, [rep], comp.xYConstructionPlane, 'patron_reperes_bas')
    mirror(comp, [rep], comp.yZConstructionPlane, 'patron_reperes_gauche')

    d.activateRootComponent()
    mn, mx = bbox_mm(body)
    print('corps', comp.bRepBodies.count, 'boite', mn, mx, 'volume cm3', round(body.volume, 2), 'en erreur', unhealthy())
    print('esquisses non contraintes', [s.name for s in comp.sketches if not s.isFullyConstrained])
    cyl = sorted(set((round(f.geometry.origin.x * 10, 2), round(f.geometry.origin.z * 10, 2), round(f.geometry.radius * 20, 2),
                      round(f.boundingBox.minPoint.y * 10, 2), round(f.boundingBox.maxPoint.y * 10, 2))
                       for f in body.faces if isinstance(f.geometry, adsk.core.Cylinder) and abs(f.geometry.axis.y) > 0.99
                       and f.geometry.radius < 1))
    print('cylindres (x, z, d, y0, y1)', cyl)
