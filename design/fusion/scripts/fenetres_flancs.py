# Fenêtres des flancs et points de fixation des plaques de flanc.
# C'est l'interface commune des plaques : fenêtre et 4 inserts identiques sur les deux flancs,
# symétriques autour du centre de la fenêtre. run() construit la coque, inserts() pose les inserts.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('fen_H', 'ouv_H', 'Fenêtre de flanc : hauteur, de pilier à pilier'),
    ('fen_P', '24 mm', 'Fenêtre de flanc : largeur, dans la profondeur de la coque'),
    ('fen_y', '( coque_Rf + coque_P ) / 2', 'Fenêtre de flanc : centre de la partie plate du flanc, depuis la façade'),
    ('flanc_vis_y', '9.5 mm', 'Plaque de flanc : demi-entraxe des vis dans la profondeur'),
    ('flanc_vis_z', '42 mm', 'Plaque de flanc : demi-entraxe vertical des vis, dans les piliers'),
    ('flanc_vis_p', '8 mm', 'Coque : profondeur du perçage des inserts de plaque de flanc'),
]

INSERT = 'urn:adsk.wipprod:dm.lineage:GK5OA6dNQ2GUaPnln4oKqQ'


def spt(sk, u, v):
    """Ici, les outils de lib.py travaillent en coordonnées d'esquisse (plan parallèle à YZ)."""
    return P3(u, v, 0)


def coque_occ():
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    return [o for o in design().rootComponent.occurrences if o.component.name == 'coque'][0]


def run(ctx):
    d = design()
    set_params(PARAMS)
    occ = coque_occ()
    comp = occ.component
    body = comp.bRepBodies.item(0)
    occ.activate()

    cpi = comp.constructionPlanes.createInput()
    cpi.setByOffset(comp.yZConstructionPlane, VI('coque_L / 2'))
    plan = comp.constructionPlanes.add(cpi)
    plan.name = 'plan_flanc'

    sk = sketch(comp, plan, 'fenetre_flanc')
    xp = ev('coque_L / 2')
    o = sk.modelToSketchSpace(P3(xp, 0, 0))
    py = sk.modelToSketchSpace(P3(xp, 1, 0))
    pz = sk.modelToSketchSpace(P3(xp, 0, 1))
    assert abs(o.x) < 1e-6 and abs(o.y) < 1e-6, ('origine', o.asArray())
    assert abs(py.x - o.x) < 1e-6 and abs(pz.y - o.y) < 1e-6, ('axes', py.asArray(), pz.asArray())
    sy = 1 if py.y > o.y else -1              # y modèle = sy * y esquisse ; z modèle sur x esquisse
    nx = sk.xDirection.crossProduct(sk.yDirection).x
    inward = NEG if nx > 0 else POS

    rect(sk, 'fen_H', 'fen_P', 'fen_H / 2', 'fen_y - fen_P / 2', sx=-1, sz=-sy, cx=0, cz=sy * ev('fen_y'))
    cut = extrude(comp, sk.profiles.item(0), CUT, 'coque_L / 2 - ouv_L / 2', inward, 'fenetre_flanc', [body])

    sk2 = sketch(comp, plan, 'inserts_flanc')
    cy = sy * ev('fen_y')
    ctr = sk2.sketchPoints.add(P3(0, cy, 0))
    sk2.sketchDimensions.addDistanceDimension(sk2.originPoint, ctr, VER, P3(0.4, cy / 2, 0)).parameter.expression = 'fen_y'
    sk2.geometricConstraints.addVerticalPoints(sk2.originPoint, ctr)
    pts = four_points(sk2, ctr, 0, cy, 'flanc_vis_z', 'flanc_vis_y')

    hf = comp.features.holeFeatures
    hi = hf.createCounterboreInput(VI('vis_d'), VI('insert_d'), VI('insert_p'))
    coll = adsk.core.ObjectCollection.create()
    for p in pts:
        coll.add(p)
    hi.setPositionBySketchPoints(coll)
    hi.setDistanceExtent(VI('flanc_vis_p'))
    hi.isDefaultDirection = nx > 0            # par défaut, à l'opposé de la normale de l'esquisse
    hi.participantBodies = [body]
    h = hf.add(hi)
    h.name = 'inserts_flanc'
    h.tipAngle.expression = '180 deg'

    mirror(comp, [cut, h], comp.yZConstructionPlane, 'flanc_miroir')
    d.activateRootComponent()
    print('sy', sy, 'nx', nx, 'corps', comp.bRepBodies.count, 'faces', body.faces.count,
          'vol cm3', round(body.volume, 2), 'alertes', unhealthy())


def inserts(ctx):
    """8 inserts dans le composant visserie, chacun lié au centre de son logement."""
    d = design()
    root = d.rootComponent
    occ = coque_occ()
    vocc = [o for o in root.occurrences if o.component.name == 'visserie'][0]
    laiton = d.appearances.itemByName('Laiton poli')
    xf = ev('coque_L / 2')
    r = ev('insert_d') / 2
    edges, seen = [], set()
    for e in occ.bRepBodies.item(0).edges:
        g = e.geometry
        if isinstance(g, adsk.core.Circle3D) and abs(g.radius - r) < 1e-4 and abs(abs(g.center.x) - xf) < 1e-4:
            k = (round(g.center.x, 3), round(g.center.y, 3), round(g.center.z, 3))
            if k not in seen:
                seen.add(k)
                edges.append(e)
    assert len(edges) == 8, len(edges)
    df = app.data.findFileById(INSERT)
    flips = 0
    for i, e in enumerate(edges):
        sub = vocc.component.occurrences.addByInsert(df, adsk.core.Matrix3D.create(), True)
        sub.isGroundToParent = False
        o = sub.createForAssemblyContext(vocc)
        o.appearance = laiton
        out = 1 if e.geometry.center.x > 0 else -1

        def joint(flip):
            g1 = adsk.fusion.JointGeometry.createByPoint(
                sub.component.originConstructionPoint.createForAssemblyContext(o))
            g2 = adsk.fusion.JointGeometry.createByCurve(e, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
            ji = root.joints.createInput(g1, g2)
            ji.setAsRigidJointMotion()
            ji.isFlipped = flip
            j = root.joints.add(ji)
            j.name = 'inserts_flanc_%d' % (i + 1)
            return j

        j = joint(False)
        p, x, y, z = o.transform2.getAsCoordinateSystem()
        if z.x * out < 0:                     # le +Z du modèle doit sortir du logement
            j.deleteMe()
            j = joint(True)
            flips += 1
            p, x, y, z = o.transform2.getAsCoordinateSystem()
        if p.distanceTo(e.geometry.center) > 1e-4 or z.x * out < 0.999:
            raise RuntimeError('insert %d mal placé : %s %s' % (i + 1, p.asArray(), z.asArray()))
    print('inserts posés', len(edges), 'retournés', flips, 'visserie', vocc.component.occurrences.count,
          'alertes', unhealthy())
