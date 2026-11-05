# Plaque de flanc encastrée à fleur du flanc, après plaque_flanc.py.
# La plaque (3 mm) est plus épaisse que la paroi (2,5 mm) : la feuillure traverse la paroi côté
# mur, d'où une nervure d'appui. Les inserts partent du fond de la feuillure, donc entièrement
# dans les piliers : leur face intérieure suit maintenant la fenêtre (pilier_z), plus ouv_H.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('plaque_bord', '1 mm', 'Flanc : bord plat gardé entre la plaque et l arrondi de la coque'),
    ('plaque_jeu', '0.15 mm', 'Plaque de flanc : jeu par côté dans la feuillure'),
    ('plaque_H', 'coque_H - 2 * coque_R - 2 * plaque_bord', 'Plaque de flanc : hauteur'),
    ('plaque_appui_z', '9 mm', 'Plaque de flanc : appui sur le flanc au-dessus et au-dessous de la fenêtre'),
    ('fen_H', 'plaque_H - 2 * plaque_appui_z', 'Fenêtre de flanc : hauteur'),
    ('pilier_z', 'fen_H / 2', 'Coque : face intérieure des piliers, au ras de la fenêtre'),
    ('flanc_vis_p', 'plaque_ep + 6 mm', 'Coque : profondeur du perçage des inserts de plaque, depuis le flanc'),
    ('flanc_nervure', '2 mm', 'Coque : épaisseur de la nervure d appui de la plaque, côté mur'),
]

_spt_modele = spt
RAW = [False]


def spt(sk, u, v):
    """Coordonnées d'esquisse en mode RAW (plans parallèles à YZ), sinon position modèle."""
    return P3(u, v, 0) if RAW[0] else _spt_modele(sk, u, v)


def plan_x(comp, expr, name):
    cpi = comp.constructionPlanes.createInput()
    cpi.setByOffset(comp.yZConstructionPlane, VI(expr))
    pl = comp.constructionPlanes.add(cpi)
    pl.name = name
    return pl


def nervure(comp, body, plan, side, suffix):
    """Nervure entre les piliers, de la fenêtre au fond ; la feuillure l'entame ensuite."""
    RAW[0] = False
    sk = sketch(comp, plan, 'nervure_' + suffix)
    w = ev('flanc_nervure + 1 mm')
    x0 = ev('coque_L / 2 - plaque_ep - flanc_nervure')
    rect(sk, 'flanc_nervure + 1 mm', 'fen_H + 1 mm', 'coque_L / 2 - plaque_ep - flanc_nervure',
         '( fen_H + 1 mm ) / 2', sx=-side, sz=-1, cx=side * (x0 + w / 2), cz=0)
    extrude(comp, sk.profiles.item(0), JOIN, 'coque_P - coque_fond - fen_y - fen_P / 2 + 0.5 mm',
            toward_wall(comp), 'nervure_' + suffix, [body])


def feuillure(comp, body, plan, side, suffix):
    RAW[0] = True
    sk = sketch(comp, plan, 'feuillure_' + suffix)
    xp = side * ev('coque_L / 2')
    o = sk.modelToSketchSpace(P3(xp, 0, 0))
    py = sk.modelToSketchSpace(P3(xp, 1, 0))
    pz = sk.modelToSketchSpace(P3(xp, 0, 1))
    assert abs(o.x) < 1e-6 and abs(o.y) < 1e-6, ('origine', o.asArray())
    assert abs(py.x - o.x) < 1e-6 and abs(pz.y - o.y) < 1e-6, ('axes', py.asArray(), pz.asArray())
    sy = 1 if py.y > o.y else -1
    nx = sk.xDirection.crossProduct(sk.yDirection).x
    inward = (NEG if nx > 0 else POS) if side > 0 else (POS if nx > 0 else NEG)
    rect(sk, 'plaque_H + 2 * plaque_jeu', 'plaque_P + 2 * plaque_jeu', '( plaque_H + 2 * plaque_jeu ) / 2',
         'fen_y - ( plaque_P + 2 * plaque_jeu ) / 2', sx=-1, sz=-sy, cx=0, cz=sy * ev('fen_y'))
    extrude(comp, sk.profiles.item(0), CUT, 'plaque_ep', inward, 'feuillure_' + suffix, [body])
    RAW[0] = False
    hz = ev('plaque_H / 2 + plaque_jeu')
    hy = ev('plaque_P / 2 + plaque_jeu')
    yc = ev('fen_y')
    edges = []
    for e in body.edges:
        if not isinstance(e.geometry, adsk.core.Line3D):
            continue
        a, b = e.startVertex.geometry, e.endVertex.geometry
        if abs(a.y - b.y) > 1e-4 or abs(a.z - b.z) > 1e-4 or a.x * side < 0:
            continue
        if abs(abs(a.z) - hz) < 1e-3 and abs(abs(a.y - yc) - hy) < 1e-3:
            edges.append(e)
    assert len(edges) == 4, ('coins de feuillure', len(edges))
    fillet(comp, edges, 'plaque_R + plaque_jeu', 'feuillure_coins_' + suffix)


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    root = d.rootComponent
    occ = [o for o in root.occurrences if o.component.name == 'coque'][0]
    comp = occ.component
    body = comp.bRepBodies.item(0)

    # 1. Libérer les inserts : leurs arêtes d'accroche disparaissent avec la feuillure.
    inserts = []
    for j in [j for j in root.joints if j.name.startswith('inserts_flanc_')]:
        o = j.occurrenceOne
        t = o.transform2.translation
        inserts.append((j.name, o, t.x, t.y, t.z))
        j.deleteMe()
    assert len(inserts) == 8, len(inserts)

    # 2. Cotes commandées par la plaque, piliers, perçages et position de la plaque.
    set_params(PARAMS)
    sk = comp.sketches.itemByName('pilier')
    for dm in sk.sketchDimensions:
        e = dm.parameter.expression.replace(' ', '')
        if e == '(coque_H-coque_ep-ouv_H)/2':
            dm.parameter.expression = '( coque_H - coque_ep ) / 2 - pilier_z'
        elif e == 'ouv_H/2':
            dm.parameter.expression = 'pilier_z'
    comp.features.holeFeatures.itemByName('inserts_flanc (1)').counterboreDepth.expression = 'plaque_ep + insert_p'
    for n in ('jo_plaque_flanc_droite', 'jo_plaque_flanc_gauche'):
        root.jointOrigins.itemByName(n).offsetZ.expression = 'coque_L / 2 - plaque_ep'

    # 3. Nervures et feuillures, dans la coque.
    occ.activate()
    body = comp.bRepBodies.item(0)
    plan_n = plane_y(comp, 'fen_y + fen_P / 2', 'plan_nervure')
    plan_d = comp.constructionPlanes.itemByName('plan_flanc')
    plan_g = plan_x(comp, '-coque_L / 2', 'plan_flanc_gauche')
    for side, plan, suffix in ((1, plan_d, 'droite'), (-1, plan_g, 'gauche')):
        nervure(comp, body, plan_n, side, suffix)
        body = comp.bRepBodies.item(0)
        feuillure(comp, body, plan, side, suffix)
        body = comp.bRepBodies.item(0)
    d.activateRootComponent()

    # 4. Relier les inserts au fond de la feuillure.
    xf = ev('coque_L / 2 - plaque_ep')
    r = ev('insert_d') / 2
    edges, seen = [], set()
    for e in occ.bRepBodies.item(0).edges:
        g = e.geometry
        if isinstance(g, adsk.core.Circle3D) and abs(g.radius - r) < 1e-4 and abs(abs(g.center.x) - xf) < 1e-4:
            k = (round(g.center.x, 3), round(g.center.y, 3), round(g.center.z, 3))
            if k not in seen:
                seen.add(k)
                edges.append(e)
    assert len(edges) == 8, ('logements', len(edges))
    flips = 0
    for name, o, tx, ty, tz in inserts:
        same = [e for e in edges if e.geometry.center.x * tx > 0 and e.geometry.center.z * tz > 0]
        e = min(same, key=lambda q: abs(q.geometry.center.y - ty))
        edges.remove(e)
        out = 1 if tx > 0 else -1

        def joint(flip):
            g1 = adsk.fusion.JointGeometry.createByPoint(o.component.originConstructionPoint.createForAssemblyContext(o))
            g2 = adsk.fusion.JointGeometry.createByCurve(e, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
            ji = root.joints.createInput(g1, g2)
            ji.setAsRigidJointMotion()
            ji.isFlipped = flip
            j = root.joints.add(ji)
            j.name = name
            return j

        j = joint(False)
        p, x, y, z = o.transform2.getAsCoordinateSystem()
        if z.x * out < 0:
            j.deleteMe()
            j = joint(True)
            flips += 1
            p, x, y, z = o.transform2.getAsCoordinateSystem()
        if p.distanceTo(e.geometry.center) > 1e-4 or z.x * out < 0.999:
            raise RuntimeError('%s mal placé : %s %s' % (name, p.asArray(), z.asArray()))
    print('inserts reliés', len(inserts), 'retournés', flips, 'corps coque', comp.bRepBodies.count,
          'vol', round(comp.bRepBodies.item(0).volume, 2), 'alertes', unhealthy())
