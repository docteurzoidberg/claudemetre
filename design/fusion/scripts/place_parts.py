# Étape 1d : apparences des pièces imprimées + insertion des 2 SO-45 et du TM1637,
# placés par liaisons rigides sur des origines de liaison pilotées par les paramètres.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

APP_LIB = 'BA5EE55E-9982-449B-9D66-9F036540E140'
SO45 = 'urn:adsk.wipprod:dm.lineage:Uwb-Qf22QsS6yuSEYtVmZw'
TM1637 = 'urn:adsk.wipprod:dm.lineage:l3rPYkDxRfWAsndd_VzZfA'


def appearance(name, src_id, rgb=None):
    d = design()
    a = d.appearances.itemByName(name)
    if a:
        return a
    src = app.materialLibraries.itemById(APP_LIB).appearances.itemById(src_id)
    a = d.appearances.addByCopy(src, name)
    if rgb:
        for i in range(a.appearanceProperties.count):
            p = a.appearanceProperties.item(i)
            if isinstance(p, adsk.core.ColorProperty) and p.id in ('opaque_albedo', 'generic_diffuse'):
                p.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
    return a


def occ_named(name):
    for o in design().rootComponent.occurrences:
        if o.component.name == name:
            return o


def joint_origin(name, x_e, y_e, z_e, z_axis=None, x_axis=None, flip=False):
    root = design().rootComponent
    inp = root.jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(root.originConstructionPoint))
    inp.offsetX = VI(x_e)
    inp.offsetY = VI(y_e)
    inp.offsetZ = VI(z_e)
    if z_axis is not None:
        inp.zAxisEntity = z_axis
    if x_axis is not None:
        inp.xAxisEntity = x_axis
    inp.isFlipped = flip
    jo = root.jointOrigins.add(inp)
    jo.name = name
    return jo


def place(df, name, jo, angle=None):
    root = design().rootComponent
    occ = root.occurrences.addByInsert(df, adsk.core.Matrix3D.create(), True)
    occ.isGroundToParent = False
    geo = adsk.fusion.JointGeometry.createByPoint(
        occ.component.originConstructionPoint.createForAssemblyContext(occ))
    ji = root.joints.createInput(geo, jo)
    ji.setAsRigidJointMotion()
    j = root.joints.add(ji)
    j.name = name
    if angle:
        j.angle.expression = angle
    return occ, j


def frame(occ):
    o, x, y, z = occ.transform2.getAsCoordinateSystem()
    f = lambda v, k=1: [round(c * k, 2) for c in v.asArray()]
    return 'o%s x%s y%s z%s' % (f(o, 10), f(x), f(y), f(z))


def run(ctx):
    d = design()
    root = d.rootComponent
    kaki = appearance('PLA kaki', 'Prism-118', (92, 98, 60))
    noir = appearance('PLA noir', 'Prism-113', (30, 30, 30))
    for name, a in (('coque', kaki), ('platine', noir), ('plaquette_session', noir),
                    ('plaquette_semaine', noir), ('plaquette_reinit', noir)):
        occ_named(name).component.bRepBodies.item(0).appearance = a

    so45 = app.data.findFileById(SO45)
    out = []
    for side, sx in (('droite', ''), ('gauche', '-')):
        jo = joint_origin('jo_jauge_' + side, sx + 'jauge_x', '-platine_ep', 'jauge_z')
        occ, j = place(so45, 'jauge_' + side, jo, '180 deg')
        out.append('jauge_%s %s' % (side, frame(occ)))
        for b in occ.bRepBodies:
            bb = b.boundingBox
            out.append('   %s %s z[%.1f, %.1f] y[%.1f, %.1f]' % (b.name, b.appearance.name, bb.minPoint.z * 10,
                                                               bb.maxPoint.z * 10, bb.minPoint.y * 10, bb.maxPoint.y * 10))
    jo = joint_origin('jo_afficheur', 'aff_x', '-platine_ep - aff_saillie', 'aff_z',
                      z_axis=root.yConstructionAxis, x_axis=root.xConstructionAxis, flip=True)
    occ, j = place(app.data.findFileById(TM1637), 'afficheur', jo)
    out.append('afficheur %s' % frame(occ))
    out.append('unhealthy %s' % unhealthy())
    print('\n'.join(out))
