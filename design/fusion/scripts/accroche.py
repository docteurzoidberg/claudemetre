# Accroche murale : deux trous de serrure dans le fond de la coque. Les têtes des vis
# à bois de la planche entrent par les grands trous, le boîtier descend, la tige remonte dans la
# fente et la tête reste derrière le fond. Tout traverse le fond : pas de support à l'impression.
# À mesurer sur les vraies vis : accroche_tete_d, accroche_tige_d (paramètres favoris).
# run() les a posés dans l'axe des SO-45 ; mi_hauteur() a ensuite amené les vis à mi-hauteur.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('accroche_tete_d', '8 mm', 'Accroche : diamètre de la tête de la vis à bois, à mesurer'),
    ('accroche_tige_d', '4 mm', 'Accroche : diamètre de la vis juste sous la tête, à mesurer'),
    ('accroche_jeu', '0.3 mm', 'Accroche : jeu par côté, de la tête dans le grand trou et de la tige dans la fente'),
    ('accroche_recouvrement', '2 mm', 'Accroche : appui de la tête au-delà du grand trou, boîtier accroché'),
    ('accroche_x', 'jauge_x', 'Accroche : demi-entraxe des vis, dans l\'axe des SO-45'),
    ('accroche_z', 'jauge_z', 'Accroche : hauteur du haut de la fente (centre de son arrondi), dans l\'axe des SO-45'),
    ('accroche_course', 'accroche_tete_d + accroche_jeu + accroche_recouvrement',
     'Accroche : descente du boîtier, du centre du grand trou au centre de l\'arrondi de la fente'),
]


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    set_params(PARAMS)
    for n in ('accroche_tete_d', 'accroche_tige_d'):
        d.userParameters.itemByName(n).isFavorite = True
    occ = [o for o in d.rootComponent.occurrences if o.component.name == 'coque'][0]
    comp = occ.component
    body = comp.bRepBodies.item(0)
    v0 = body.volume
    occ.activate()
    plan = comp.constructionPlanes.itemByName('plan_fond')
    wall = toward_wall(comp)

    # Grand trou : position cotée depuis le haut de la fente, pour rester juste si la course
    # fait passer son centre de l'autre côté de z = 0.
    sk = sketch(comp, plan, 'accroche_trou')
    haut, x, z = point(sk, 'accroche_x', 'accroche_z')
    zb = z - ev('accroche_course')
    rt = ev('accroche_tete_d + 2 * accroche_jeu') / 2
    c = sk.sketchCurves.sketchCircles.addByCenterRadius(spt(sk, x, zb), rt)
    g, dm = sk.geometricConstraints, sk.sketchDimensions
    g.addVerticalPoints(haut, c.centerSketchPoint)
    dm.addDistanceDimension(haut, c.centerSketchPoint, VER, spt(sk, x + rt + 0.5, (z + zb) / 2)).parameter.expression = 'accroche_course'
    dm.addDiameterDimension(c, spt(sk, x + rt + 0.3, zb - rt - 0.3)).parameter.expression = 'accroche_tete_d + 2 * accroche_jeu'
    assert sk.profiles.count == 1, sk.profiles.count
    trou = extrude(comp, sk.profiles.item(0), CUT, 'coque_fond', wall, 'accroche_trou_coupe', [body])

    # Fente : deux flancs, l'arrondi du haut, et un bas droit noyé dans le grand trou.
    sk = sketch(comp, plan, 'accroche_fente')
    r = ev('accroche_tige_d + 2 * accroche_jeu') / 2
    L = sk.sketchCurves.sketchLines
    gauche = L.addByTwoPoints(spt(sk, x - r, zb), spt(sk, x - r, z))
    droite = L.addByTwoPoints(spt(sk, x + r, z), spt(sk, x + r, zb))
    bas = L.addByTwoPoints(droite.endSketchPoint, gauche.startSketchPoint)
    arc = sk.sketchCurves.sketchArcs.addByThreePoints(gauche.endSketchPoint, spt(sk, x, z + r), droite.startSketchPoint)
    g, dm = sk.geometricConstraints, sk.sketchDimensions
    g.addVertical(gauche)
    g.addVertical(droite)
    g.addHorizontal(bas)
    ctr = arc.centerSketchPoint
    dm.addDistanceDimension(sk.originPoint, ctr, HOR, spt(sk, x / 2, z + r + 0.3)).parameter.expression = 'accroche_x'
    dm.addDistanceDimension(sk.originPoint, ctr, VER, spt(sk, x + r + 0.8, z / 2)).parameter.expression = 'accroche_z'
    g.addHorizontalPoints(ctr, gauche.endSketchPoint)
    g.addHorizontalPoints(ctr, droite.startSketchPoint)
    dm.addDistanceDimension(gauche.endSketchPoint, droite.startSketchPoint, HOR,
                            spt(sk, x, z + r + 0.6)).parameter.expression = 'accroche_tige_d + 2 * accroche_jeu'
    dm.addDistanceDimension(ctr, bas.startSketchPoint, VER, spt(sk, x + r + 0.5, (z + zb) / 2)).parameter.expression = 'accroche_course'
    assert sk.profiles.count == 1, sk.profiles.count
    contraint = sk.isFullyConstrained
    fente = extrude(comp, sk.profiles.item(0), CUT, 'coque_fond', wall, 'accroche_fente_coupe', [body])

    mirror(comp, [trou, fente], comp.yZConstructionPlane, 'accroche_miroir')
    d.activateRootComponent()
    print('esquisse fente contrainte', contraint, 'corps', comp.bRepBodies.count,
          'volume retiré mm3', round((v0 - body.volume) * 1000, 1), 'en erreur', unhealthy())


def mi_hauteur(ctx):
    """Vis à mi-hauteur de la coque, boîtier accroché. Le boîtier pend sur sa tige : l'arrondi de la
    fente est à accroche_jeu sous l'axe de la vis. Cote prise depuis le haut de la coque, car
    une cote depuis l'origine ne vaut rien à z = 0 et ne change pas de côté."""
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    comp = [o for o in d.rootComponent.occurrences if o.component.name == 'coque'][0].component
    H = ev('coque_H / 2')
    for name in ('accroche_trou', 'accroche_fente'):
        sk = comp.sketches.itemByName(name)
        old = [x for x in sk.sketchDimensions if x.parameter.expression == 'accroche_z']
        assert len(old) == 1, (name, len(old))
        old = adsk.fusion.SketchLinearDimension.cast(old[0])
        pt = old.entityTwo if old.entityOne == sk.originPoint else old.entityOne
        ref = sk.sketchPoints.add(spt(sk, 0, H))
        sk.geometricConstraints.addVerticalPoints(sk.originPoint, ref)
        dm = sk.sketchDimensions
        dm.addDistanceDimension(sk.originPoint, ref, VER, spt(sk, -0.5, H / 2)).parameter.expression = 'coque_H / 2'
        old.deleteMe()
        x = ev('accroche_x')
        dm.addDistanceDimension(ref, pt, VER, spt(sk, x + 1.2, H / 2)).parameter.expression = 'coque_H / 2 - accroche_z + accroche_jeu'
        print(name, 'contraint', sk.isFullyConstrained)
    set_params([('accroche_z', '0 mm', 'Accroche : hauteur de l\'axe des vis, boîtier accroché (0 = mi-hauteur de la coque)')])
    print('en erreur', unhealthy())
