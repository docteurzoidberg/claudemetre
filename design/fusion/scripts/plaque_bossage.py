# Plaque de flanc « bossage incliné », composant plaque_bossage : le connecteur regarde 30° vers le haut.
# Même interface que plaque_flanc : ses paramètres donnent le contour, 3 mm logés dans la feuillure, le
# dépassement et les 4 vis (CHC M3×6). Le LP-16 repose directement sur le coin kaki, descendu de
# bossage_decalage le long de la face pour que son ergot passe le rail. Il se fixe par 4 FHC M3×12.
#
# Repère de plaque_flanc : à plat sur XY, origine au centre de la face d'appui, face visible vers +Z,
# X dans la profondeur de la coque, Y en hauteur. La plaque est symétrique en X : un seul composant pour
# les deux flancs. Attention, sur le flanc gauche la liaison de plaque_flanc met Y vers le bas.
import adsk.core, adsk.fusion, math, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('bossage_face', '33 mm', 'Plaque bossage : longueur de la face inclinée'),
    ('bossage_rail', 'plaque_saillie', 'Plaque bossage : dépassement des rails sur le flanc, comme la plaque générique'),
    ('bossage_decalage', '1.5 mm', 'Plaque bossage : connecteur descendu le long de la face, pour que l ergot passe le rail'),
    ('bossage_pied', 'flanc_vis_z - plaque_lamage_d / 2 - 1 mm', 'Plaque bossage : pied de la pente sous le centre, 1 mm après le lamage'),
    ('bossage_saillie', 'bossage_rail + bossage_face * sin(bossage_angle)', 'Plaque bossage : dépassement de l arête sur le flanc'),
    ('bossage_crete', 'bossage_pied - ( bossage_saillie - bossage_rail )', 'Plaque bossage : arête sous le centre, pente à 45°'),
    ('bossage_haut', 'bossage_face * cos(bossage_angle) - bossage_crete', 'Plaque bossage : pied de la face inclinée au-dessus du centre'),
    ('bossage_paroi', '3 mm', 'Plaque bossage : paroi sous la pente'),
    ('bossage_paroi_face', '6 mm', 'Plaque bossage : paroi sous la face inclinée, logements d inserts compris'),
    ('bossage_creux_k', '( plaque_ep + bossage_saillie ) * cos(bossage_angle) - bossage_crete * sin(bossage_angle) - bossage_paroi_face',
     'Plaque bossage : distance de l origine au fond de la paroi de face'),
    ('bossage_creux_m', 'plaque_ep + bossage_rail + bossage_pied - bossage_paroi * sqrt(2)', 'Plaque bossage : ligne intérieure de la pente'),
    ('bossage_creux_y', '( bossage_creux_m * cos(bossage_angle) - bossage_creux_k ) / ( cos(bossage_angle) + sin(bossage_angle) )',
     'Plaque bossage : sommet du creux sous le centre'),
    ('bossage_percage', '16.5 mm', 'Plaque bossage : perçage du connecteur LP-16'),
    ('bossage_vis', '20 mm', 'Plaque bossage : entraxe des 4 vis du connecteur LP-16'),
]


def spt(sk, u, v):
    """Ici, les outils de lib.py travaillent en coordonnées d'esquisse."""
    return P3(u, v, 0)


def pyz(sk, y, z):
    """Point d'esquisse du plan YZ pour (Y, Z) du composant."""
    p = sk.modelToSketchSpace(P3(0, y, z))
    return P3(p.x, p.y, 0)


def poly(sk, pts):
    L = sk.sketchCurves.sketchLines
    ls = [L.addByTwoPoints(pts[0], pts[1])]
    for p in pts[2:]:
        ls.append(L.addByTwoPoints(ls[-1].endSketchPoint, p))
    ls.append(L.addByTwoPoints(ls[-1].endSketchPoint, ls[0].startSketchPoint))
    return ls


def cote(sk, pt, sens, expr):
    """Cote depuis l'origine de l'esquisse."""
    g = pt.geometry
    t = P3(g.x / 2 + 0.3, g.y / 2 + 0.3, 0)
    sk.sketchDimensions.addDistanceDimension(sk.originPoint, pt, sens, t).parameter.expression = expr


def plan_yz(comp, name):
    sk = sketch(comp, comp.yZConstructionPlane, name)
    o, y, z = sk.modelToSketchSpace(P3(0, 0, 0)), sk.modelToSketchSpace(P3(0, 1, 0)), sk.modelToSketchSpace(P3(0, 0, 1))
    assert abs(y.x - o.x) < 1e-6 and abs(z.y - o.y) < 1e-6, ('axes du plan YZ', y.asArray(), z.asArray())
    return sk


def extrude_sym(comp, prof, op, largeur, name, bodies=None):
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(prof, op)
    inp.setSymmetricExtent(VI(largeur), True)
    if bodies is not None:
        inp.participantBodies = bodies
    f = ext.add(inp)
    f.name = name
    return f


def is_corner_edge(e, w, h):
    if not isinstance(e.geometry, adsk.core.Line3D):
        return False
    a, b = e.startVertex.geometry, e.endVertex.geometry
    if abs(a.x - b.x) > 1e-4 or abs(a.y - b.y) > 1e-4:
        return False
    return abs(abs(a.x) - w / 2) < 1e-3 and abs(abs(a.y) - h / 2) < 1e-3


def aretes_exterieures(body):
    """Arêtes vives du dessus : tour des rails, flancs du coin et arête. Pas les pieds, qui sont rentrants."""
    w, h = ev('plaque_P') / 2, ev('plaque_H') / 2
    zr, zs = ev('plaque_ep + bossage_rail'), ev('plaque_ep + bossage_saillie')
    out = []
    for e in body.edges:
        a, b = e.startVertex.geometry, e.endVertex.geometry
        if min(a.z, b.z) < zr - 1e-4:
            continue
        cote_plat = abs(a.x - b.x) < 1e-4 and abs(abs(a.x) - w) < 1e-4
        bout = abs(a.y - b.y) < 1e-4 and abs(abs(a.y) - h) < 1e-4
        arete = abs(a.z - zs) < 1e-4 and abs(b.z - zs) < 1e-4
        coin = isinstance(e.geometry, adsk.core.Arc3D)
        if cote_plat or bout or arete or coin:
            out.append(e)
    return out


def construit(comp, d):
    # Base : même contour que plaque_flanc, rails compris.
    sk = sketch(comp, comp.xYConstructionPlane, 'plaque')
    centered_rect(sk, 'plaque_P', 'plaque_H')
    body = extrude(comp, sk.profiles.item(0), NEW, 'plaque_ep + bossage_rail', POS, 'plaque').bodies.item(0)
    body.name = 'plaque_bossage'
    assert body.boundingBox.minPoint.z > -1e-4, 'extrusion du mauvais côté'
    fillet(comp, [e for e in body.edges if is_corner_edge(e, ev('plaque_P'), ev('plaque_H'))], 'plaque_R', 'plaque_coins')

    # Coin : l'arête en bas, la face regarde vers le haut et l'extérieur.
    zr, zs = ev('plaque_ep + bossage_rail'), ev('plaque_ep + bossage_saillie')
    yh, yc, yp = ev('bossage_haut'), -ev('bossage_crete'), -ev('bossage_pied')
    sk = plan_yz(comp, 'bossage')
    a, b, c, dd, e = (pyz(sk, y, z) for y, z in ((yh, zr - 0.1), (yh, zr), (yc, zs), (yp, zr), (yp, zr - 0.1)))
    ls = poly(sk, [a, b, c, dd, e])
    ab, bc, cd, de, ea = ls
    g = sk.geometricConstraints
    g.addHorizontal(ab); g.addHorizontal(de); g.addVertical(ea)
    cote(sk, ab.startSketchPoint, HOR, 'plaque_ep + bossage_rail - 1 mm')
    cote(sk, ab.startSketchPoint, VER, 'bossage_haut')
    cote(sk, ab.endSketchPoint, HOR, 'plaque_ep + bossage_rail')
    cote(sk, ea.startSketchPoint, VER, 'bossage_pied')
    g.addVerticalPoints(ab.endSketchPoint, de.startSketchPoint)
    cote(sk, bc.endSketchPoint, HOR, 'plaque_ep + bossage_saillie')
    cote(sk, bc.endSketchPoint, VER, 'bossage_crete')
    centre = sk.sketchPoints.add(pyz(sk, (yh + yc) / 2, (zr + zs) / 2))
    g.addCoincident(centre, bc)
    q = centre.geometry
    sk.sketchDimensions.addDistanceDimension(bc.endSketchPoint, centre, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                             P3(q.x - 0.6, q.y - 0.6, 0)).parameter.expression = 'bossage_face / 2 - bossage_decalage'
    extrude_sym(comp, sk.profiles.item(0), JOIN, 'plaque_P', 'bossage', [body])
    body = comp.bRepBodies.item(0)
    assert comp.bRepBodies.count == 1, comp.bRepBodies.count

    # Creux : la largeur de la fenêtre, ouvert au dos, sans descendre sous la fenêtre.
    ya, yb = ev('bossage_creux_k / sin(bossage_angle)'), -ev('bossage_creux_y')
    zb, zc, yf = ev('bossage_creux_m - bossage_creux_y'), ev('bossage_creux_m - fen_H / 2'), -ev('fen_H / 2')
    sk = plan_yz(comp, 'creux')
    ls = poly(sk, [pyz(sk, ya, 0), pyz(sk, yb, zb), pyz(sk, yf, zc), pyz(sk, yf, 0)])
    pa, pb, pc, pd = ls
    g = sk.geometricConstraints
    g.addHorizontal(pc); g.addVertical(pd)
    g.addVerticalPoints(sk.originPoint, pa.startSketchPoint)
    cote(sk, pa.startSketchPoint, VER, 'bossage_creux_k / sin(bossage_angle)')
    cote(sk, pb.startSketchPoint, HOR, 'bossage_creux_m - bossage_creux_y')
    cote(sk, pb.startSketchPoint, VER, 'bossage_creux_y')
    cote(sk, pc.startSketchPoint, HOR, 'bossage_creux_m - fen_H / 2')
    cote(sk, pc.startSketchPoint, VER, 'fen_H / 2')
    extrude_sym(comp, sk.profiles.item(0), CUT, 'fen_P', 'creux', [body])
    body = comp.bRepBodies.item(0)
    assert comp.bRepBodies.count == 1, comp.bRepBodies.count
    fillet(comp, aretes_exterieures(body), 'plaque_Rf', 'plaque_arrondi')
    body = comp.bRepBodies.item(0)
    return body, bc, centre


def connecteur(comp, body, ligne, centre):
    """Plan de la face inclinée, perçage du connecteur et logements d'inserts. Tout part de points d'esquisse :
    un profil tiré d'un point projeté reste figé à l'ancienne place, sans alerte, quand le point bouge."""
    cpi = comp.constructionPlanes.createInput()
    cpi.setByAngle(ligne, VI('90 deg'), comp.yZConstructionPlane)
    plan = comp.constructionPlanes.add(cpi)
    plan.name = 'plan_face_inclinee'
    sk = sketch(comp, plan, 'face')
    ctr = sk.project(centre).item(0)
    c = ctr.geometry
    pts = four_points(sk, ctr, c.x, c.y, 'bossage_vis / 2', 'bossage_vis / 2')
    entree = sk.xDirection.crossProduct(sk.yDirection).z > 0
    hf = comp.features.holeFeatures

    def perce(hi, points, name):
        coll = adsk.core.ObjectCollection.create()
        for p in points:
            coll.add(p)
        hi.setPositionBySketchPoints(coll)
        hi.setDistanceExtent(VI('bossage_paroi_face + 1 mm'))
        hi.isDefaultDirection = entree
        hi.participantBodies = [body]
        h = hf.add(hi)
        h.name = name
        h.tipAngle.expression = '180 deg'

    perce(hf.createCounterboreInput(VI('vis_d'), VI('insert_d'), VI('insert_p')), pts, 'inserts_connecteur')
    perce(hf.createSimpleInput(VI('bossage_percage')), [ctr], 'percage_connecteur')


def vis_plaque(comp, body):
    """4 perçages de plaque_flanc ; le lamage garde la tête à la même place que sur la plaque générique."""
    cpi = comp.constructionPlanes.createInput()
    cpi.setByOffset(comp.xYConstructionPlane, VI('plaque_ep + bossage_rail'))
    plan = comp.constructionPlanes.add(cpi)
    plan.name = 'plan_rails'
    sk = sketch(comp, plan, 'vis')
    pts = four_points(sk, sk.originPoint, 0, 0, 'flanc_vis_y', 'flanc_vis_z')
    hf = comp.features.holeFeatures
    hi = hf.createCounterboreInput(VI('vis_d'), VI('plaque_lamage_d'), VI('plaque_lamage_p + bossage_rail - plaque_saillie'))
    coll = adsk.core.ObjectCollection.create()
    for p in pts:
        coll.add(p)
    hi.setPositionBySketchPoints(coll)
    hi.setDistanceExtent(VI('plaque_ep + bossage_rail'))
    hi.isDefaultDirection = sk.xDirection.crossProduct(sk.yDirection).z > 0
    hi.participantBodies = [body]
    hv = hf.add(hi)
    hv.name = 'plaque_vis'
    hv.tipAngle.expression = '180 deg'


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    root = d.rootComponent
    assert not [c for c in d.allComponents if c.name == 'plaque_bossage'], 'déjà construite'
    if not d.userParameters.itemByName('bossage_angle'):
        d.userParameters.add('bossage_angle', VI('30 deg'), 'deg', 'Plaque bossage : connecteur au-dessus de l horizontale')
    set_params(PARAMS)

    occ = new_component('plaque_bossage')
    occ.isGroundToParent = False
    comp = occ.component
    occ.activate()
    body, ligne, centre = construit(comp, d)
    connecteur(comp, body, ligne, centre)
    body = comp.bRepBodies.itemByName('plaque_bossage')
    vis_plaque(comp, body)
    d.activateRootComponent()

    def corps(nom):
        return [o for o in root.occurrences if o.component.name == nom][0].component.bRepBodies.item(0)
    comp.bRepBodies.itemByName('plaque_bossage').appearance = corps('coque').appearance

    ji = root.joints.createInput(adsk.fusion.JointGeometry.createByPoint(
        comp.originConstructionPoint.createForAssemblyContext(occ)), root.jointOrigins.itemByName('jo_plaque_flanc_droite'))
    ji.setAsRigidJointMotion()
    root.joints.add(ji).name = 'plaque_bossage_droite'
    o, x, y, z = occ.transform2.getAsCoordinateSystem()
    want = P3(ev('coque_L / 2 - plaque_ep'), ev('fen_y'), 0)
    if o.distanceTo(want) > 1e-4 or z.x < 0.999 or y.z < 0.999:
        raise RuntimeError('plaque mal placée : o=%s x=%s y=%s z=%s' % (
            [round(v * 10, 2) for v in o.asArray()], x.asArray(), y.asArray(), z.asArray()))
    root.occurrences.itemByName('plaque_flanc:1').isLightBulbOn = False

    print('corps', [(b.name, round(b.volume, 3), b.faces.count) for b in comp.bRepBodies], 'alertes', unhealthy())
    print('params', {p: round(ev(p) * 10, 2) for p in ('bossage_saillie', 'bossage_crete', 'bossage_haut', 'bossage_creux_k',
                                                       'bossage_creux_m', 'bossage_creux_y')})


def modele(nom):
    dst = app.activeDocument.dataFile.parentFolder.dataFolders.itemByName('models')
    return {dst.dataFiles.item(i).name: dst.dataFiles.item(i) for i in range(dst.dataFiles.count)}[nom]


def pose_connecteur(ctx, nom='connecteur_LP-16_2poles'):
    """Insère un LP-16 de models/ : bride sur la face inclinée, ergot vers le haut de la pente.
    Repère du modèle : origine au centre de la face arrière de la bride, +Z vers la fiche, +Y vers l'ergot."""
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    root = d.rootComponent
    occ = [o for o in root.occurrences if o.component.name == 'plaque_bossage'][0]
    sk = occ.component.sketches.itemByName('face')
    ctr = [p for p in sk.sketchPoints if p.isReference][0].createForAssemblyContext(occ)

    lp = root.occurrences.addByInsert(modele(nom), adsk.core.Matrix3D.create(), True)
    lp.isGroundToParent = False
    n, u = axes(d)
    want = ctr.worldGeometry
    for flip in (False, True):
        for ang in ('0 deg', '90 deg', '180 deg', '270 deg'):
            ji = root.joints.createInput(
                adsk.fusion.JointGeometry.createByPoint(lp.component.originConstructionPoint.createForAssemblyContext(lp)),
                adsk.fusion.JointGeometry.createByPoint(ctr))
            ji.setAsRigidJointMotion()
            ji.isFlipped = flip
            ji.angle = VI(ang)
            j = root.joints.add(ji)
            j.name = 'lp16_bossage'
            o, x, y, z = lp.transform2.getAsCoordinateSystem()
            if o.distanceTo(want) < 1e-3 and z.dotProduct(n) > 0.999 and y.dotProduct(u) > 0.999:
                noir = [q for q in root.occurrences if q.component.name == 'platine'][0].component.bRepBodies.item(0).appearance
                for b in lp.bRepBodies:   # le STEP porte ses couleurs : celle de l'occurrence ne suffit pas
                    b.appearance = noir
                print('posé', nom, 'retourné', flip, 'angle', ang, [round(v * 10, 2) for v in o.asArray()], 'alertes', unhealthy())
                return lp
            j.deleteMe()
    raise RuntimeError('aucune pose ne convient')


def axes(d):
    """Normale de la face inclinée et direction du haut de la pente, dans le repère du design (plaque à droite)."""
    a = d.unitsManager.evaluateExpression('bossage_angle', 'rad')
    return adsk.core.Vector3D.create(math.cos(a), 0, math.sin(a)), adsk.core.Vector3D.create(-math.sin(a), 0, math.cos(a))


def lier(root, vocc, df, edge, n, nom, apparence, offset=None):
    """Une pièce de visserie liée au centre d'une arête circulaire, son +Z sortant du perçage."""
    sub = vocc.component.occurrences.addByInsert(df, adsk.core.Matrix3D.create(), True)
    sub.isGroundToParent = False
    o = sub.createForAssemblyContext(vocc)
    o.appearance = apparence

    def joint(flip):
        ji = root.joints.createInput(
            adsk.fusion.JointGeometry.createByPoint(sub.component.originConstructionPoint.createForAssemblyContext(o)),
            adsk.fusion.JointGeometry.createByCurve(edge, adsk.fusion.JointKeyPointTypes.CenterKeyPoint))
        ji.setAsRigidJointMotion()
        ji.isFlipped = flip
        if offset:
            ji.offset = adsk.core.ValueInput.createByString(offset)
        j = root.joints.add(ji)
        j.name = nom
        return j

    j = joint(False)
    p, x, y, z = o.transform2.getAsCoordinateSystem()
    if z.dotProduct(n) < 0:
        j.deleteMe()
        j = joint(True)
        p, x, y, z = o.transform2.getAsCoordinateSystem()
    ecart = abs(j.offset.value) if offset else 0
    if abs(p.distanceTo(edge.geometry.center) - ecart) > 1e-4 or z.dotProduct(n) < 0.999:
        raise RuntimeError('%s mal placé : %s %s' % (nom, p.asArray(), z.asArray()))


def visserie_connecteur(ctx):
    """4 inserts dans les logements et 4 FHC M3×12 dans les fraisures de la bride du LP-16."""
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    root = d.rootComponent
    occ = [o for o in root.occurrences if o.component.name == 'plaque_bossage'][0]
    lp = [o for o in root.occurrences if o.component.name.startswith('connecteur_LP-16')][0]
    vocc = [o for o in root.occurrences if o.component.name == 'visserie'][0]
    n, _ = axes(d)

    def hauteur(e):
        return e.geometry.center.asVector().dotProduct(n)

    def cercles(body, r):
        out = [e for e in body.edges if isinstance(e.geometry, adsk.core.Circle3D) and abs(e.geometry.radius - r) < 1e-4
               and abs(abs(e.geometry.normal.dotProduct(n)) - 1) < 1e-4]
        top = max(hauteur(e) for e in out)
        return [e for e in out if abs(hauteur(e) - top) < 1e-3]

    logements = cercles(occ.bRepBodies.item(0), ev('insert_d') / 2)
    bride = max(lp.bRepBodies, key=lambda b: b.volume)
    fraisures = cercles(bride, 0.3)
    assert len(logements) == 4 and len(fraisures) == 4, (len(logements), len(fraisures))
    laiton, noir = d.appearances.itemByName('Laiton poli'), d.appearances.itemByName('Oxyde noir')
    for i, e in enumerate(logements):
        lier(root, vocc, modele('insert_chaud_M3'), e, n, 'insert_connecteur_%d' % (i + 1), laiton)
    for i, e in enumerate(fraisures):
        # La tête dépasse de la bride : le modèle a un bord cylindrique de 0,2 que la fraisure n'a pas.
        lier(root, vocc, modele('vis_FHC_M3x12'), e, n, 'vis_connecteur_%d' % (i + 1), noir, '-0.2 mm')
    print('visserie', vocc.component.occurrences.count, 'alertes', unhealthy())
