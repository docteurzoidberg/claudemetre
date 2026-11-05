# Plaque de flanc à fusible, composant plaque_bossage_fusible : LP-16 et porte-fusible 5 × 20, axes parallèles
# à 45°, sur deux faces en marche, forme « Gorge » retenue le 05/11/2026. Le fusible protège l'arrivée 12 V.
# Même interface que plaque_flanc. Le composant rassemble la plaque, le connecteur, le porte-fusible et leur
# visserie : on l'affiche ou on le masque d'un bloc, à la place des autres plaques.
#
# Contour, partie logée, dépassement et vis viennent des paramètres de plaque_flanc, lus à la construction.
# Les cotes de forme sont en tête de ce fichier, pas dans les paramètres du design : pour en changer, supprimer
# le composant et relancer. Repère de plaque_flanc : à plat sur XY, origine au centre de la face d'appui, face
# visible vers +Z, X dans la profondeur de la coque, Y en hauteur.
#
# Profil : s le long de la face du LP-16 depuis son pied haut, t sous cette face.
import adsk.core, adsk.fusion, math, os

PB = os.path.join(os.path.dirname(__file__), 'plaque_bossage.py')
exec(compile(open(PB, encoding='utf-8').read(), PB, 'exec'))

V3 = adsk.core.Vector3D.create
JG = adsk.fusion.JointGeometry
NOM = 'plaque_bossage_fusible'

ANGLE = 45.0            # axes au-dessus de l'horizontale : vers 46°, le pied haut atteint les lamages
PIED = 34.4             # pied haut de la face du LP-16, au-dessus du centre de la plaque
FACE = 34.0             # longueur de la face du LP-16 : 1,75 de marge sous la bride, comme sur les côtés
LP_S = 18.0             # centre du LP-16 sur la face
MARCHE = 20.0           # face du fusible sous celle du LP-16
FUSIBLE_S = 8.5         # axe du fusible après la fin de la face du LP-16 : 1 entre collerette et bossage
R_COIN, R_NEZ, R_ARETE = 4.5, 8.0, 0.5
R_TUBE, R_ALESAGE, R_PERCAGE = 11.0, 9.0, 5.75   # perçage : filet Ø 11 sur le modèle, à confirmer sur la pièce
R_GORGE, LEVRE = 10.0, 2.5                       # la gorge s'arrête sous la face du LP-16 : marge intacte
ECROU, EMPREINTE = 15.3, 3.5                     # 15 sur plats ; rondelles 1 + écrou 2,5
PAROI_FACE, PAROI_MARCHE, PAROI_FUSIBLE = 6.0, 4.5, 4.0
COLLERETTE = 10.0       # du zéro du modèle à l'arrière de la collerette


def axes():
    """Normale des faces et haut de la pente, dans le repère du design (plaque à droite)."""
    a = math.radians(ANGLE)
    return V3(math.cos(a), 0, math.sin(a)), V3(-math.sin(a), 0, math.cos(a))


def plaque(comp):
    a = math.radians(ANGLE)
    s, c = math.sin(a), math.cos(a)
    logee, ep = ev('plaque_ep'), ev('plaque_ep + bossage_rail') * 10
    W, H = ev('plaque_P') * 5, ev('plaque_H') / 2
    SC = FACE + FUSIBLE_S

    def plate(sv, t, yv=0.0):
        return P3(yv / 10, (PIED - sv * c - t * s) / 10, (ep + sv * s - t * c) / 10)

    sk = sketch(comp, comp.xYConstructionPlane, 'plaque')
    centered_rect(sk, 'plaque_P', 'plaque_H')
    body = extrude(comp, sk.profiles.item(0), NEW, 'plaque_ep + bossage_rail', POS, 'plaque').bodies.item(0)
    body.name = NOM
    assert body.boundingBox.minPoint.z > -1e-4, 'extrusion du mauvais côté'
    fillet(comp, [e for e in body.edges if is_corner_edge(e, ev('plaque_P'), ev('plaque_H'))], 'plaque_R', 'plaque_coins')

    # Droites de construction des deux faces et centre du LP-16.
    sk = plan_yz(comp, 'axes')

    def pz(sv, t):
        q = plate(sv, t)
        return pyz(sk, q.y, q.z)
    f1 = sk.sketchCurves.sketchLines.addByTwoPoints(pz(0, 0), pz(FACE, 0))
    f1.isConstruction = True
    f2 = sk.sketchCurves.sketchLines.addByTwoPoints(pz(FACE, MARCHE), pz(FACE + 2 * FUSIBLE_S, MARCHE))
    f2.isConstruction = True
    centre = sk.sketchPoints.add(pz(LP_S, 0))

    cpi = comp.constructionPlanes.createInput()
    cpi.setByAngle(f2, VI('90 deg'), comp.yZConstructionPlane)
    plan = comp.constructionPlanes.add(cpi)
    plan.name = 'plan_face_fusible'
    dehors_pos = plan.geometry.normal.dotProduct(V3(0, s, c)) > 0
    dedans, dehors = (NEG, POS) if dehors_pos else (POS, NEG)

    def plan_t(t, nom):
        i = comp.constructionPlanes.createInput()
        i.setByOffset(plan, VI('%g mm' % (-t if dehors_pos else t)))
        p = comp.constructionPlanes.add(i)
        p.name = nom
        return p

    def q_(k, sv, yv, t):
        r = k.modelToSketchSpace(plate(sv, t, yv))
        return P3(r.x, r.y, 0)

    def cercle(pl, nom, r_mm, t):
        k = sketch(comp, pl, nom)
        k.sketchCurves.sketchCircles.addByCenterRadius(q_(k, SC, 0, t), r_mm / 10)
        return k

    def fermer(k, pts, t):
        L = k.sketchCurves.sketchLines
        first = l = L.addByTwoPoints(q_(k, pts[0][0], pts[0][1], t), q_(k, pts[1][0], pts[1][1], t))
        for p in pts[2:]:
            l = L.addByTwoPoints(l.endSketchPoint, q_(k, p[0], p[1], t))
        L.addByTwoPoints(l.endSketchPoint, first.startSketchPoint)

    def goutte(pl):
        """Section du tube : flancs tangents aux coins du bossage, nez de rayon R_NEZ, fond plat."""
        k = sketch(comp, pl, 'goutte')
        ca = (FACE - R_COIN, W - R_COIN)
        cb = (SC + R_TUBE - R_NEZ, R_TUBE - R_NEZ)
        dx, dy = cb[0] - ca[0], cb[1] - ca[1]
        dist = math.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        kk = (R_COIN - R_NEZ) / dist
        m = math.sqrt(1 - kk * kk)
        n = (kk * ux - m * uy, kk * uy + m * ux)
        ta = (ca[0] + R_COIN * n[0], ca[1] + R_COIN * n[1])
        tb = (cb[0] + R_NEZ * n[0], cb[1] + R_NEZ * n[1])
        L = k.sketchCurves.sketchLines

        def arc(p0, mid, p1):
            fin = q_(k, p1[0], p1[1], MARCHE)
            a_ = k.sketchCurves.sketchArcs.addByThreePoints(p0, q_(k, mid[0], mid[1], MARCHE), fin)
            return a_.endSketchPoint if a_.endSketchPoint.geometry.distanceTo(fin) < 1e-6 else a_.startSketchPoint

        def milieu(sign):
            am = math.atan2(sign * n[1], n[0]) / 2
            return (cb[0] + R_NEZ * math.cos(am), sign * (cb[1] + R_NEZ * abs(math.sin(am))))

        l1 = L.addByTwoPoints(q_(k, ta[0], -ta[1], MARCHE), q_(k, tb[0], -tb[1], MARCHE))
        p = arc(l1.endSketchPoint, milieu(-1), (SC + R_TUBE, -cb[1]))
        l_ = L.addByTwoPoints(p, q_(k, SC + R_TUBE, cb[1], MARCHE))
        p = arc(l_.endSketchPoint, milieu(1), (tb[0], tb[1]))
        l2 = L.addByTwoPoints(p, q_(k, ta[0], ta[1], MARCHE))
        L.addByTwoPoints(l2.endSketchPoint, l1.startSketchPoint)
        return k

    def largest(sk_):
        return max(sk_.profiles, key=lambda p: p.areaProperties().area)

    # Coin pleine largeur : face du LP-16, puis retour au flanc parallèle à l'axe.
    sk = plan_yz(comp, 'bossage')
    q, r = plate(FACE, 0), plate(FACE, FACE * s / c)
    poly(sk, [pyz(sk, y, z) for y, z in ((PIED / 10, logee), (PIED / 10, ep / 10), (q.y, q.z), (r.y, ep / 10), (r.y, logee))])
    extrude_sym(comp, largest(sk), JOIN, '%g mm' % (2 * W), 'bossage', [body])
    body = comp.bRepBodies.item(0)
    assert comp.bRepBodies.count == 1
    coins = []
    for e in body.edges:
        if isinstance(e.geometry, adsk.core.Line3D):
            p, q2 = e.startVertex.geometry, e.endVertex.geometry
            if abs(abs(p.x) - W / 10) < 1e-4 and abs(abs(q2.x) - W / 10) < 1e-4:
                dy_, dz_ = q2.y - p.y, q2.z - p.z
                ln = math.hypot(dy_, dz_)
                if ln > 0.5 and abs(abs(dy_ / ln * s + dz_ / ln * c) - 1) < 1e-4:
                    coins.append(e)
    assert len(coins) == 2, len(coins)
    fillet(comp, coins, '%g mm' % R_COIN, 'coins_bas_bossage')
    body = comp.bRepBodies.item(0)

    # Tube du fusible, arasé au dos et en bas de la plaque.
    extrude(comp, largest(goutte(plan)), JOIN, '70 mm', dedans, 'tube', [body])
    body = comp.bRepBodies.item(0)
    k = sketch(comp, comp.xYConstructionPlane, 'arase')
    k.sketchCurves.sketchLines.addTwoPointRectangle(P3(-6, -8, 0), P3(6, 8, 0))
    extrude(comp, k.profiles.item(0), CUT, '80 mm', NEG, 'arase_dos', [body])
    body = comp.bRepBodies.item(0)
    if body.boundingBox.minPoint.y < -H - 1e-4:
        k = sketch(comp, comp.xYConstructionPlane, 'arase_bas')
        k.sketchCurves.sketchLines.addTwoPointRectangle(P3(-6, -7, 0), P3(6, -H, 0))
        extrude(comp, k.profiles.item(0), CUT, 'plaque_ep + bossage_rail', POS, 'arase_bas', [body])
        body = comp.bRepBodies.item(0)
    assert body.boundingBox.minPoint.y > -H - 1e-4 and body.boundingBox.minPoint.z > -1e-4

    # Creux derrière le LP-16, de la largeur de la fenêtre.
    sk = plan_yz(comp, 'creux')
    sf = FACE - PAROI_MARCHE
    h1, h2, h3 = plate((PAROI_FACE * c - ep) / s, PAROI_FACE), plate(sf, PAROI_FACE), plate(sf, (sf * s + ep) / c)
    poly(sk, [pyz(sk, p.y, p.z) for p in (h1, h2, h3)])
    extrude_sym(comp, largest(sk), CUT, 'fen_P', 'creux', [body])
    body = comp.bRepBodies.item(0)

    # Gorge autour du capuchon.
    k = cercle(plan, 'gorge', R_GORGE, MARCHE)
    extrude(comp, k.profiles.item(0), CUT, '%g mm' % (MARCHE - LEVRE), dehors, 'gorge', [body])
    body = comp.bRepBodies.item(0)

    # Arêtes : le tour de la face du LP-16, le tour de la face du fusible, puis les rails.
    def t_de(p):
        return (p.y * 10 - PIED) * s + (p.z * 10 - ep) * c

    def s_de(p):
        return -(p.y * 10 - PIED) * c + (p.z * 10 - ep) * s

    def dans(e, t):
        return abs(t_de(e.startVertex.geometry) + t) < 1e-3 and abs(t_de(e.endVertex.geometry) + t) < 1e-3

    def rond_coin(e):
        return any(isinstance(f.geometry, adsk.core.Cylinder) and abs(f.geometry.radius - R_COIN / 10) < 1e-4 for f in e.faces)

    zr, wp, hp = ep / 10, ev('plaque_P') / 2, H
    e1, e2, e3 = [], [], []
    for e in body.edges:
        p, q2 = e.startVertex.geometry, e.endVertex.geometry
        if dans(e, 0):
            if not (abs(p.z - zr) < 1e-4 and abs(q2.z - zr) < 1e-4):    # pas les pieds, rentrants, sur le rail
                e1.append(e)
        elif dans(e, MARCHE):
            g = e.geometry
            if isinstance(g, (adsk.core.Arc3D, adsk.core.Circle3D)):
                if abs(g.radius - R_NEZ / 10) < 1e-4:
                    e2.append(e)
            elif not rond_coin(e) and not (abs(s_de(p) - FACE) < 1e-3 and abs(s_de(q2) - FACE) < 1e-3):
                e2.append(e)
        elif abs(p.z - zr) < 1e-4 and abs(q2.z - zr) < 1e-4:
            if (abs(p.x - q2.x) < 1e-4 and abs(abs(p.x) - wp) < 1e-4) or (abs(p.y - q2.y) < 1e-4 and abs(abs(p.y) - hp) < 1e-4) \
                    or (isinstance(e.geometry, adsk.core.Arc3D) and abs(e.geometry.radius - 0.3) < 1e-4):
                e3.append(e)
    print('arêtes', len(e1), len(e2), len(e3))
    ff = comp.features.filletFeatures
    inp = ff.createInput()
    for lst in (e1, e2, e3):
        coll = adsk.core.ObjectCollection.create()
        for e in lst:
            coll.add(e)
        inp.edgeSetInputs.addConstantRadiusEdgeSet(coll, VI('%g mm' % R_ARETE), True)
    ff.add(inp).name = 'arrondis'
    body = comp.bRepBodies.item(0)

    # Intérieur du tube : alésage, empreinte de l'écrou (on visse par l'extérieur), perçage du filet.
    t1 = PAROI_FUSIBLE + EMPREINTE
    k = cercle(plan_t(t1, 'plan_alesage'), 'alesage', R_ALESAGE, MARCHE + t1)
    extrude(comp, k.profiles.item(0), CUT, '70 mm', dedans, 'alesage', [body])
    body = comp.bRepBodies.item(0)
    f = plate(SC, MARCHE)
    if f.y * 10 - f.z * 10 * s / c - R_ALESAGE / c < -40:
        # L'alésage toucherait le bas de la plaque : bande refermée dessous.
        k = sketch(comp, comp.xYConstructionPlane, 'bande_bas')
        k.sketchCurves.sketchLines.addTwoPointRectangle(P3(-0.8, -H + 0.05, 0), P3(0.8, -H + 0.3, 0))
        extrude(comp, k.profiles.item(0), JOIN, 'plaque_ep + bossage_rail', POS, 'bande_bas', [body])
        body = comp.bRepBodies.item(0)
    rc = ECROU / 2 / math.cos(math.radians(30))
    k = sketch(comp, plan_t(PAROI_FUSIBLE, 'plan_empreinte'), 'empreinte')
    fermer(k, [(SC - rc * math.sin(math.radians(60 * i - 60)), rc * math.cos(math.radians(60 * i - 60))) for i in range(6)],
           MARCHE + PAROI_FUSIBLE)
    extrude(comp, k.profiles.item(0), CUT, '%g mm' % EMPREINTE, dedans, 'empreinte_ecrou', [body])
    body = comp.bRepBodies.item(0)
    k = cercle(plan, 'percage_fusible', R_PERCAGE, MARCHE)
    extrude(comp, k.profiles.item(0), CUT, '%g mm' % PAROI_FUSIBLE, dedans, 'percage_fusible', [body])
    body = comp.bRepBodies.item(0)

    connecteur(comp, body, f1, centre)
    vis_plaque(comp, comp.bRepBodies.item(0))


def occ_plaque():
    return [o for o in design().rootComponent.occurrences if o.component.name == NOM][0]


def run(ctx):
    """Construit la plaque et la pose sur le flanc droit. Elle reste à part : pose_lp16, pose_fusible et
    affiche font la suite."""
    assert app.activeDocument.name == 'claudometre', app.activeDocument.name
    d = design()
    root = d.rootComponent
    assert not [c for c in d.allComponents if c.name == NOM], 'déjà construite'
    occ = new_component(NOM)
    occ.isGroundToParent = False
    comp = occ.component
    occ.activate()
    plaque(comp)
    d.activateRootComponent()
    comp.bRepBodies.item(0).appearance = [o for o in root.occurrences if o.component.name == 'coque'][0].component.bRepBodies.item(0).appearance
    ji = root.joints.createInput(JG.createByPoint(comp.originConstructionPoint.createForAssemblyContext(occ)),
                                 root.jointOrigins.itemByName('jo_plaque_flanc_droite'))
    ji.setAsRigidJointMotion()
    root.joints.add(ji).name = NOM + '_droite'
    o, x, y, z = occ.transform2.getAsCoordinateSystem()
    want = P3(ev('coque_L / 2 - plaque_ep'), ev('fen_y'), 0)
    if o.distanceTo(want) > 1e-4 or z.x < 0.999 or y.z < 0.999:
        raise RuntimeError('plaque mal placée : %s %s %s' % (o.asArray(), y.asArray(), z.asArray()))
    b = comp.bRepBodies.item(0)
    print(NOM, 'faces', b.faces.count, 'volume', round(b.volume * 1000), 'corps', comp.bRepBodies.count, 'alertes', unhealthy())


def _pose(root, sub, o, cible, n, y_voulu, nom, decalages=(None,)):
    """Liaison rigide de l'origine du modèle sur un point d'esquisse, en essayant les sens possibles."""
    want = cible.worldGeometry
    for flip in (False, True):
        for off in decalages:
            for ang in ('0 deg', '90 deg', '180 deg', '270 deg'):
                ji = root.joints.createInput(JG.createByPoint(sub.component.originConstructionPoint.createForAssemblyContext(o)),
                                             JG.createByPoint(cible))
                ji.setAsRigidJointMotion()
                ji.isFlipped = flip
                ji.angle = VI(ang)
                if off:
                    ji.offset = VI(off)
                j = root.joints.add(ji)
                j.name = nom
                p, x, y, z = o.transform2.getAsCoordinateSystem()
                ecart = abs(j.offset.value) if off else 0
                dessus = want.copy()
                v = n.copy()
                v.scaleBy(ecart)
                dessus.translateBy(v)
                if p.distanceTo(dessus) < 1e-3 and z.dotProduct(n) > 0.999 and y.dotProduct(y_voulu) > 0.999:
                    print('posé', nom, 'retourné', flip, 'angle', ang, 'décalage', off, [round(k * 10, 2) for k in p.asArray()])
                    return
                j.deleteMe()
    raise RuntimeError('aucune pose ne convient pour ' + nom)


def pose_lp16(ctx):
    """LP-16 dans le composant : bride sur la face, ergot vers le haut de la pente, puis 4 inserts et 4 FHC M3×12."""
    assert app.activeDocument.name == 'claudometre', app.activeDocument.name
    d = design()
    root = d.rootComponent
    occ = occ_plaque()
    comp = occ.component
    n, u = axes()
    ctr = [p for p in comp.sketches.itemByName('face').sketchPoints if p.isReference][0].createForAssemblyContext(occ)
    sub = comp.occurrences.addByInsert(modele('connecteur_LP-16_2poles'), adsk.core.Matrix3D.create(), True)
    sub.isGroundToParent = False
    lp = sub.createForAssemblyContext(occ)
    _pose(root, sub, lp, ctr, n, u, 'lp16_fusible')
    noir = [q for q in root.occurrences if q.component.name == 'platine'][0].component.bRepBodies.item(0).appearance
    for b in lp.bRepBodies:   # le STEP porte ses couleurs : celle de l'occurrence ne suffit pas
        b.appearance = noir

    def hauteur(e):
        return e.geometry.center.asVector().dotProduct(n)

    def cercles(body, r):
        out = [e for e in body.edges if isinstance(e.geometry, adsk.core.Circle3D) and abs(e.geometry.radius - r) < 1e-4
               and abs(abs(e.geometry.normal.dotProduct(n)) - 1) < 1e-4]
        top = max(hauteur(e) for e in out)
        return [e for e in out if abs(hauteur(e) - top) < 1e-3]

    logements = cercles(occ.bRepBodies.item(0), ev('insert_d') / 2)
    fraisures = cercles(max(lp.bRepBodies, key=lambda b: b.volume), 0.3)
    assert len(logements) == 4 and len(fraisures) == 4, (len(logements), len(fraisures))
    laiton, oxyde = d.appearances.itemByName('Laiton poli'), d.appearances.itemByName('Oxyde noir')
    for i, e in enumerate(logements):
        lier(root, occ, modele('insert_chaud_M3'), e, n, 'insert_fusible_%d' % (i + 1), laiton)
    for i, e in enumerate(fraisures):
        lier(root, occ, modele('vis_FHC_M3x12'), e, n, 'vis_fusible_%d' % (i + 1), oxyde, '-0.2 mm')
    print('occurrences', comp.occurrences.count, 'alertes', unhealthy())


def pose_fusible(ctx):
    """Porte-fusible dans le composant, collerette sur la face, cosses sur les côtés (quart de tour)."""
    assert app.activeDocument.name == 'claudometre', app.activeDocument.name
    root = design().rootComponent
    occ = occ_plaque()
    comp = occ.component
    n, _ = axes()
    ctr = comp.sketches.itemByName('percage_fusible').sketchCurves.sketchCircles.item(0).centerSketchPoint.createForAssemblyContext(occ)
    sub = comp.occurrences.addByInsert(modele('porte_fusible_5x20'), adsk.core.Matrix3D.create(), True)
    sub.isGroundToParent = False
    o = sub.createForAssemblyContext(occ)
    _pose(root, sub, o, ctr, n, V3(0, 1, 0), 'porte_fusible', ('%g mm' % COLLERETTE, '%g mm' % -COLLERETTE))
    print('occurrences', comp.occurrences.count, 'corps fusible', o.bRepBodies.count, o.childOccurrences.count, 'alertes', unhealthy())


def affiche(ctx):
    """Une seule plaque visible sur le flanc droit : celle-ci."""
    assert app.activeDocument.name == 'claudometre', app.activeDocument.name
    root = design().rootComponent
    root.occurrences.itemByName('plaque_bossage:1').isLightBulbOn = False
    occ_plaque().isLightBulbOn = True


def controle(ctx):
    """Lecture seule : interférences du composant avec tout le reste, et entre ses pièces."""
    assert app.activeDocument.name == 'claudometre', app.activeDocument.name
    root = design().rootComponent
    tbm = adsk.fusion.TemporaryBRepManager.get()
    occ = occ_plaque()

    def corps(o):
        return [(o.name.split(':')[0], b) for b in o.bRepBodies]

    dedans = corps(occ)
    for c in occ.childOccurrences:
        dedans += corps(c)
        for c2 in c.childOccurrences:
            dedans += corps(c2)
    zone = dedans[0][1].boundingBox.copy()
    for _, b in dedans:
        zone.combine(b.boundingBox)
    autres = []
    for o in root.allOccurrences:
        top = o.fullPathName.split('+')[0]
        if top in (occ.name, 'plaque_bossage:1', 'plaque_flanc:1', 'patron:1') or not zone.intersects(o.boundingBox):
            continue
        autres += [(top.split(':')[0], b) for b in o.bRepBodies if zone.intersects(b.boundingBox)]
    tot = {}

    def inter(n1, a, n2, b):
        if not a.boundingBox.intersects(b.boundingBox):
            return
        x, y = tbm.copy(a), tbm.copy(b)
        try:
            tbm.booleanOperation(x, y, adsk.fusion.BooleanTypes.IntersectionBooleanType)
        except Exception:
            return
        if x.faces.count:
            k = tuple(sorted((n1, n2)))
            tot[k] = tot.get(k, 0) + x.volume * 1000

    for n1, a in dedans:
        for n2, b in autres:
            inter(n1, a, n2, b)
    for i, (n1, a) in enumerate(dedans):
        for n2, b in dedans[i + 1:]:
            if n1 != n2:
                inter(n1, a, n2, b)
    r = {'%s / %s' % k: round(v, 2) for k, v in tot.items()} or 'aucune interférence'
    open(os.path.join(os.environ['TEMP'], 'claudemetre', 'check_fusible.txt'), 'w', encoding='utf-8').write(str(r) + ' / voisins %d' % len(autres))
    print(r, 'voisins', len(autres))
