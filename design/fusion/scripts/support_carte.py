# Support de la carte à borniers. Trois clips collés dans des logements
# creusés dans le fond de la coque, la carte MRD076A + ESP32 clipsée dessus, debout, antenne en
# haut, grand crochet en haut. logements() creuse la coque, clips() dérive les trois clips du
# design `support carte esp - rteverse` et les place, carte() insère le modèle mrd076a_esp32_s3.
# Cotes des clips : leur repère est celui du design source, base en z = 0, grand crochet vers +X.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

SUPPORT = 'support carte esp - rteverse'
CARTE = 'urn:adsk.wipprod:dm.lineage:ud3QBHJfRDuQ8BlnBFmM1w'

PARAMS = [
    ('carte_L', '84.7 mm', 'Carte à borniers : longueur du circuit, debout dans la coque'),
    ('carte_W', '73.6 mm', 'Carte à borniers : largeur du circuit'),
    ('carte_jeu', '0.1 mm', 'Carte à borniers : jeu par côté contre les butées des ailes'),
    ('clip_L', '88.1 mm', 'Clip : longueur totale'),
    ('clip_bas', '78.1 mm', 'Clip : de son origine au bout du petit crochet'),
    ('clip_z0', '33.85 mm', 'Clip : hauteur de son origine dans la coque, logement de la carte centré sur z = 0'),
    ('clip_aile_l', '12.5 mm', 'Clip aile : largeur totale'),
    ('clip_oreille', '1.5 mm', 'Clip aile : épaisseur de la butée, à l\'extérieur de la carte'),
    ('clip_mil_l', '8 mm', 'Clip milieu : largeur'),
    ('clip_appui', '6 mm', 'Clip : hauteur du dos de la carte au-dessus de la base du clip'),
    ('clip_src_y', '38 mm', 'Design source des clips : écart entre les butées des deux ailes'),
    ('clip_log_p', '1.5 mm', 'Coque : profondeur des logements des clips, dans le fond'),
    ('clip_log_jeu', '0.2 mm', 'Coque : jeu par côté des logements des clips'),
]


def coque_occ():
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    return [o for o in design().rootComponent.occurrences if o.component.name == 'coque'][0]


def logements(ctx):
    d = design()
    set_params(PARAMS)
    occ = coque_occ()
    comp = occ.component
    body = comp.bRepBodies.item(0)
    occ.activate()
    plan = plane_y(comp, 'coque_P - coque_fond', 'plan_fond')
    sk = sketch(comp, plan, 'logements_clips')
    L = 'clip_L + 2 * clip_log_jeu'
    bas = 'clip_bas - clip_z0 + clip_log_jeu'
    cz = (ev('clip_L') - 2 * ev('clip_bas') + 2 * ev('clip_z0')) / 2
    ext = 'carte_W / 2 + carte_jeu + clip_oreille + clip_log_jeu'
    aile = 'clip_aile_l + 2 * clip_log_jeu'
    cx = ev(ext) - ev(aile) / 2
    rect(sk, aile, L, ext, bas, sx=1, sz=-1, cx=cx, cz=cz)
    rect(sk, aile, L, ext, bas, sx=-1, sz=-1, cx=-cx, cz=cz)
    rect(sk, 'clip_mil_l + 2 * clip_log_jeu', L, 'clip_mil_l / 2 + clip_log_jeu', bas, sx=-1, sz=-1, cx=0, cz=cz)
    assert sk.profiles.count == 3, sk.profiles.count
    coll = adsk.core.ObjectCollection.create()
    for p in profiles(sk):
        coll.add(p)
    extrude(comp, coll, CUT, 'clip_log_p', toward_wall(comp), 'logements_clips', [body])
    d.activateRootComponent()
    print('corps', comp.bRepBodies.count, 'sante', unhealthy())


def source():
    for doc in app.documents:
        if doc.name.startswith(SUPPORT):
            return adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    raise RuntimeError('ouvrir ' + SUPPORT)


def derive(name, src, body_name):
    """Nouveau composant local dont le corps suit le design source. Le corps dérivé va dans le
    composant actif, pas dans celui qui porte la fonction : activer d'abord."""
    occ = new_component(name)
    occ.isGroundToParent = False
    comp = occ.component
    occ.activate()
    di = comp.features.deriveFeatures.createInput(src)
    di.sourceEntities = [src.rootComponent.bRepBodies.itemByName(body_name)]
    comp.features.deriveFeatures.add(di)
    design().activateRootComponent()
    return occ


def joint_origin(name, x_e, y_e, z_e, x_axis):
    """Origine de liaison sur la racine, Z vers la façade ; décalages dans son propre repère."""
    root = design().rootComponent
    inp = root.jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(root.originConstructionPoint))
    inp.zAxisEntity = root.yConstructionAxis
    inp.xAxisEntity = x_axis
    inp.isFlipped = True
    inp.offsetX = VI(x_e)
    inp.offsetY = VI(y_e)
    inp.offsetZ = VI(z_e)
    jo = root.jointOrigins.add(inp)
    jo.name = 'jo_' + name
    return jo


def pose(occ):
    o, x, y, z = occ.transform2.getAsCoordinateSystem()
    return [round(v * 10, 2) + 0 for v in o.asArray()], [[round(c, 3) + 0 for c in v.asArray()] for v in (x, y, z)]


def lie(occ, name, jo):
    root = design().rootComponent
    ji = root.joints.createInput(adsk.fusion.JointGeometry.createByPoint(
        occ.component.originConstructionPoint.createForAssemblyContext(occ)), jo)
    ji.setAsRigidJointMotion()
    root.joints.add(ji).name = name


BASE = 'coque_P - coque_fond + clip_log_p'
BUTEE = 'carte_W / 2 + carte_jeu'
CLIPS = (('clip_aile', 'clip_aile', '-(%s)' % BUTEE, 36.9),
         ('clip_aile_miroir', 'clip_aile_miroir', '%s - clip_src_y' % BUTEE, 1.1),
         ('clip_milieu', 'clip_milieu', '-clip_src_y / 2', 19.0))


def clips(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    root = design().rootComponent
    src = source()
    log = []
    for name, body, off_y, x0 in CLIPS:
        occ = derive(name, src, body)
        assert occ.component.bRepBodies.count == 1, (name, occ.component.bRepBodies.count)
        lie(occ, name, joint_origin(name, 'clip_z0', off_y, '-(%s)' % BASE, root.zConstructionAxis))
        o, axes = pose(occ)
        log.append('%s o=%s axes=%s' % (name, o, axes))
        if o != [x0, 38.5, 33.85] or axes != [[0, 0, 1], [-1, 0, 0], [0, -1, 0]]:
            raise RuntimeError('pose inattendue\n' + '\n'.join(log))
        log.append('   corps %s' % (bbox_mm(occ.bRepBodies.item(0)),))
    log.append('timeline %d, en erreur %s' % (design().timeline.count, unhealthy()))
    print('\n'.join(log))


def ancre(occ):
    """Les sous-composants du modèle STEP ne suivent la liaison que s'ils sont ancrés au parent."""
    n = 0
    for c in occ.childOccurrences:
        c.nativeObject.isGroundToParent = True
        n += 1 + ancre(c)
    return n


def carte(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    root = design().rootComponent
    occ = root.occurrences.addByInsert(app.data.findFileById(CARTE), adsk.core.Matrix3D.create(), True)
    occ.isGroundToParent = False
    log = ['ancrés %d' % ancre(occ)]
    lie(occ, 'carte', joint_origin('carte', '0 mm', '-carte_L / 2', '-(%s - clip_appui)' % BASE, root.xConstructionAxis))
    o, axes = pose(occ)
    log.append('carte %s o=%s axes=%s' % (occ.name, o, axes))
    if o != [0, 32.5, -42.35] or axes != [[1, 0, 0], [0, 0, 1], [0, -1, 0]]:
        raise RuntimeError('pose inattendue\n' + '\n'.join(log))
    log.append('timeline %d, en erreur %s' % (design().timeline.count, unhealthy()))
    print('\n'.join(log))
