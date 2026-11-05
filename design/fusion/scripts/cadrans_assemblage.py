# Cadrans imprimés dans l'assemblage : les designs fond-jauge-session et
# fond-jauge-semaine, insérés comme composants externes.
# Chaque cadran est lié à son SO-45 : origine du cadran (centre de la plaque, sur l'appui des
# piliers) au centre de l'arête R 22,5 du dos de la collerette (y = 0 du SO-45, axe = axe de la
# jauge), décalée de jauge_appui le long de l'axe. Une liaison d'origine à origine ne convient
# pas : la face du cadran est sur son +Z, celle du SO-45 sur son +Y.
# Les sous-composants des variantes (fond, echelle, zone, texte) ne sont pas ancrés à leur parent :
# sans isGroundToParent, l'occurrence suit la liaison mais ses corps restent sur place. L'ancrage
# ne prend effet qu'au recalcul suivant de la liaison (changement de paramètre).
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

CADRANS = (('session', 'voltmetre_SO-45:2', -1), ('semaine', 'voltmetre_SO-45:1', 1))
FLIP = False
OFFSET = 'jauge_appui'
ANGLE = '0 deg'


def arete_collerette(g):
    for e in g.component.bRepBodies.itemByName('Body1').edges:
        c = e.geometry
        if (c.curveType == adsk.core.Curve3DTypes.Circle3DCurveType and abs(c.radius - 2.25) < 1e-4
                and abs(c.center.y) < 1e-4):
            return e.createForAssemblyContext(g)
    raise RuntimeError('arête de la collerette introuvable dans ' + g.name)


def pose(occ):
    o, x, y, z = occ.transform2.getAsCoordinateSystem()
    return [round(v * 10, 3) + 0 for v in o.asArray()], [[round(c, 3) + 0 for c in v.asArray()] for v in (x, y, z)]


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre')
    d = design()
    root = d.rootComponent
    set_params([('jauge_appui', '4 mm',
                 'haut des piliers du cadran depuis le dos de la collerette (repère du SO-45), à mesurer')])
    log = []
    for key, gauge, sign in CADRANS:
        occ = root.occurrences.itemByName('fond-jauge-%s:1' % key)
        occ.isLightBulbOn = True
        for child in occ.childOccurrences:
            child.nativeObject.isGroundToParent = True
        ji = root.joints.createInput(
            adsk.fusion.JointGeometry.createByPoint(occ.component.originConstructionPoint.createForAssemblyContext(occ)),
            adsk.fusion.JointGeometry.createByCurve(arete_collerette(root.occurrences.itemByName(gauge)),
                                                    adsk.fusion.JointKeyPointTypes.CenterKeyPoint))
        ji.setAsRigidJointMotion()
        ji.offset = VI(OFFSET)
        ji.angle = VI(ANGLE)
        ji.isFlipped = FLIP
        root.joints.add(ji).name = 'cadran_' + key
        o, axes = pose(occ)
        log.append('%s o=%s axes=%s' % (key, o, axes))
        attendu = ([sign * 58.0, -7.0, 8.0], [[1, 0, 0], [0, 0, 1], [0, -1, 0]])
        if o != attendu[0] or axes != attendu[1]:
            raise RuntimeError('pose inattendue\n' + '\n'.join(log))
    log.append('timeline %d, en erreur %s' % (d.timeline.count, unhealthy()))
    print('\n'.join(log))
