# Plaque de flanc générique (pleine), composant plaque_flanc. C'est elle qui commande
# l'interface : la fenêtre et les inserts de la coque (fenetres_flancs.py) sont exprimés à partir
# de ses cotes. run() construit et place la plaque sur les deux flancs, vis() pose les 8 vis.
#
# Repère de la plaque : à plat sur XY, origine au centre de la face d'appui, face visible vers +Z,
# X dans la profondeur de la coque, Y en hauteur.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('plaque_H', '92 mm', 'Plaque de flanc : hauteur'),
    ('plaque_P', '32 mm', 'Plaque de flanc : largeur, dans la profondeur de la coque'),
    ('plaque_ep', '3 mm', 'Plaque de flanc : épaisseur'),
    ('plaque_R', '3 mm', 'Plaque de flanc : rayon des coins'),
    ('plaque_Rf', '0.5 mm', 'Plaque de flanc : arrondi du bord de la face visible'),
    ('plaque_vis_m', '4 mm', 'Plaque de flanc : distance du centre des vis aux bords'),
    ('plaque_appui', '4 mm', 'Plaque de flanc : appui sur le flanc de chaque côté de la fenêtre'),
    ('fen_P', 'plaque_P - 2 * plaque_appui', 'Fenêtre de flanc : largeur, dans la profondeur de la coque'),
    ('flanc_vis_y', 'plaque_P / 2 - plaque_vis_m', 'Plaque de flanc : demi-entraxe des vis dans la profondeur'),
    ('flanc_vis_z', 'plaque_H / 2 - plaque_vis_m', 'Plaque de flanc : demi-entraxe vertical des vis, dans les piliers'),
]

FHC = 'urn:adsk.wipprod:dm.lineage:C7spJL_MQHyLDSNCkICQbA'


def spt(sk, u, v):
    """Ici, les outils de lib.py travaillent en coordonnées d'esquisse (plan XY)."""
    return P3(u, v, 0)


def is_corner_edge(e, w, h):
    if not isinstance(e.geometry, adsk.core.Line3D):
        return False
    a, b = e.startVertex.geometry, e.endVertex.geometry
    if abs(a.x - b.x) > 1e-4 or abs(a.y - b.y) > 1e-4:
        return False
    return abs(abs(a.x) - w / 2) < 1e-3 and abs(abs(a.y) - h / 2) < 1e-3


def place(comp, occ, side, name):
    """Liaison rigide sur le flanc : Z de la plaque vers l'extérieur, X vers le mur."""
    root = design().rootComponent
    inp = root.jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(root.originConstructionPoint))
    inp.zAxisEntity = root.xConstructionAxis
    inp.xAxisEntity = root.yConstructionAxis
    inp.isFlipped = side < 0
    inp.offsetX = VI('fen_y')
    inp.offsetY = VI('0 mm')
    inp.offsetZ = VI('coque_L / 2')
    jo = root.jointOrigins.add(inp)
    jo.name = 'jo_' + name
    ji = root.joints.createInput(adsk.fusion.JointGeometry.createByPoint(
        comp.originConstructionPoint.createForAssemblyContext(occ)), jo)
    ji.setAsRigidJointMotion()
    root.joints.add(ji).name = name
    o, x, y, z = occ.transform2.getAsCoordinateSystem()
    want = P3(side * ev('coque_L / 2'), ev('fen_y'), 0)
    if o.distanceTo(want) > 1e-4 or z.x * side < 0.999:
        raise RuntimeError('%s mal placée : o=%s x=%s y=%s z=%s' % (
            name, [round(v * 10, 2) for v in o.asArray()], x.asArray(), y.asArray(), z.asArray()))
    return 'x%s y%s z%s' % tuple([round(c, 1) for c in v.asArray()] for v in (x, y, z))


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    root = d.rootComponent
    set_params(PARAMS)

    occ = new_component('plaque_flanc')
    occ.isGroundToParent = False
    comp = occ.component
    occ.activate()

    sk = sketch(comp, comp.xYConstructionPlane, 'plaque')
    centered_rect(sk, 'plaque_P', 'plaque_H')
    body = extrude(comp, sk.profiles.item(0), NEW, 'plaque_ep', POS, 'plaque').bodies.item(0)
    body.name = 'plaque_flanc'
    assert body.boundingBox.minPoint.z > -1e-4, 'extrusion du mauvais côté'
    w, h, ep = ev('plaque_P'), ev('plaque_H'), ev('plaque_ep')
    fillet(comp, [e for e in body.edges if is_corner_edge(e, w, h)], 'plaque_R', 'plaque_coins')

    face = max((f for f in body.faces if isinstance(f.geometry, adsk.core.Plane)
                and abs(f.pointOnFace.z - ep) < 1e-4), key=lambda f: f.area)
    outer = [lp for lp in face.loops if lp.isOuter][0]
    fillet(comp, list(outer.edges), 'plaque_Rf', 'plaque_arrondi')

    cpi = comp.constructionPlanes.createInput()
    cpi.setByOffset(comp.xYConstructionPlane, VI('plaque_ep'))
    plan = comp.constructionPlanes.add(cpi)
    plan.name = 'plan_face'
    sk = sketch(comp, plan, 'vis')
    pts = four_points(sk, sk.originPoint, 0, 0, 'flanc_vis_y', 'flanc_vis_z')
    hf = comp.features.holeFeatures
    hi = hf.createCountersinkInput(VI('vis_d'), VI('fraise_d'), VI('90 deg'))
    coll = adsk.core.ObjectCollection.create()
    for p in pts:
        coll.add(p)
    hi.setPositionBySketchPoints(coll)
    hi.setDistanceExtent(VI('plaque_ep'))
    hi.isDefaultDirection = sk.xDirection.crossProduct(sk.yDirection).z > 0
    hi.participantBodies = [body]
    hv = hf.add(hi)
    hv.name = 'plaque_vis'
    hv.tipAngle.expression = '180 deg'
    d.activateRootComponent()

    body.appearance = [o for o in root.occurrences if o.component.name == 'platine'][0].component.bRepBodies.item(0).appearance
    occ2 = root.occurrences.addExistingComponent(comp, adsk.core.Matrix3D.create())
    occ2.isGroundToParent = False
    print('droite', place(comp, occ, 1, 'plaque_flanc_droite'))
    print('gauche', place(comp, occ2, -1, 'plaque_flanc_gauche'))
    print('corps', comp.bRepBodies.count, 'faces', body.faces.count, 'vol cm3', round(body.volume, 3),
          'alertes', unhealthy())


def vis(ctx):
    """8 vis FHC M3x8 dans le composant visserie, liées aux fraisures des plaques."""
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    root = d.rootComponent
    vocc = [o for o in root.occurrences if o.component.name == 'visserie'][0]
    noir = d.appearances.itemByName('Oxyde noir')
    xf = ev('coque_L / 2 + plaque_ep')
    r = ev('fraise_d') / 2
    edges = []
    for occ in [o for o in root.occurrences if o.component.name == 'plaque_flanc']:
        for e in occ.bRepBodies.item(0).edges:
            g = e.geometry
            if isinstance(g, adsk.core.Circle3D) and abs(g.radius - r) < 1e-4 and abs(abs(g.center.x) - xf) < 1e-4:
                edges.append(e)
    assert len(edges) == 8, len(edges)
    df = app.data.findFileById(FHC)
    flips = 0
    for i, e in enumerate(edges):
        sub = vocc.component.occurrences.addByInsert(df, adsk.core.Matrix3D.create(), True)
        sub.isGroundToParent = False
        o = sub.createForAssemblyContext(vocc)
        o.appearance = noir
        out = 1 if e.geometry.center.x > 0 else -1

        def joint(flip):
            g1 = adsk.fusion.JointGeometry.createByPoint(
                sub.component.originConstructionPoint.createForAssemblyContext(o))
            g2 = adsk.fusion.JointGeometry.createByCurve(e, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
            ji = root.joints.createInput(g1, g2)
            ji.setAsRigidJointMotion()
            ji.isFlipped = flip
            j = root.joints.add(ji)
            j.name = 'vis_flanc_%d' % (i + 1)
            return j

        j = joint(False)
        p, x, y, z = o.transform2.getAsCoordinateSystem()
        if z.x * out < 0:                     # le +Z du modèle doit sortir du perçage
            j.deleteMe()
            j = joint(True)
            flips += 1
            p, x, y, z = o.transform2.getAsCoordinateSystem()
        if p.distanceTo(e.geometry.center) > 1e-4 or z.x * out < 0.999:
            raise RuntimeError('vis %d mal placée : %s %s' % (i + 1, p.asArray(), z.asArray()))
    print('vis posées', len(edges), 'retournées', flips, 'visserie', vocc.component.occurrences.count,
          'alertes', unhealthy())
