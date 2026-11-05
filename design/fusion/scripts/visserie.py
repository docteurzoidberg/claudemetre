# Étape 1e : inserts et vis M3, dans le composant « visserie », chacun lié (liaison rigide) au
# centre de l'arête circulaire du perçage qui le reçoit : ils suivent les paramètres.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

APP_LIB = 'BA5EE55E-9982-449B-9D66-9F036540E140'
F = {
    'insert': 'urn:adsk.wipprod:dm.lineage:GK5OA6dNQ2GUaPnln4oKqQ',
    'fhc8': 'urn:adsk.wipprod:dm.lineage:C7spJL_MQHyLDSNCkICQbA',
    'chc12': 'urn:adsk.wipprod:dm.lineage:TBhioc-rRUWGKOde7sFNzw',
    'chc6': 'urn:adsk.wipprod:dm.lineage:aAxEYmdfS_mcqoZ7HgwAAg',
}
# groupe : (modèle, occurrence cible, corps cible ou None, rayon de l'arête (mm), y de l'arête (expr),
#           sens de pénétration (+1 = vers le mur), nombre attendu, apparence)
GROUPS = {
    'inserts_coque': ('insert', 'coque', None, 2.1, '0 mm', 1, 4, 'laiton'),
    'vis_platine': ('fhc8', 'platine', None, 3.2, '-platine_ep', 1, 4, 'noir'),
    'inserts_jauges': ('insert', 'platine', None, 2.1, 'jauge_bossage_h', -1, 8, 'laiton'),
    'inserts_afficheur': ('insert', 'platine', None, 2.1, 'aff_bossage_h', -1, 4, 'laiton'),
    'inserts_plaquettes': ('insert', 'platine', None, 2.1, 'plaq_bossage_h', -1, 6, 'laiton'),
    'vis_plaquettes': ('fhc8', 'plaquette_', None, 3.2, '-platine_ep - plaq_ep', 1, 6, 'noir'),
    'vis_jauges': ('chc12', 'voltmetre_SO-45', 'Body1', 2.0, '-platine_ep - 4.65 mm', 1, 8, 'noir'),
    'vis_afficheur': ('chc6', 'afficheur_TM1637', 'Body16', 1.65, 'aff_bossage_h + 1.6 mm', -1, 4, None),
}


def lib_appearance(name, src_id):
    d = design()
    a = d.appearances.itemByName(name)
    if not a:
        a = d.appearances.addByCopy(app.materialLibraries.itemById(APP_LIB).appearances.itemById(src_id), name)
    return a


def edges_for(prefix, body_name, r_mm, y_cm):
    root = design().rootComponent
    out, seen = [], set()
    for occ in root.occurrences:
        if not occ.component.name.startswith(prefix):
            continue
        for b in occ.bRepBodies:
            if body_name and b.name != body_name:
                continue
            for e in b.edges:
                g = e.geometry
                if isinstance(g, adsk.core.Circle3D) and abs(g.radius * 10 - r_mm) < 0.01 \
                        and abs(g.center.y - y_cm) < 1e-3:
                    k = (round(g.center.x, 3), round(g.center.z, 3))
                    if k not in seen:
                        seen.add(k)
                        out.append(e)
    return out


def visserie_occ():
    root = design().rootComponent
    for o in root.occurrences:
        if o.component.name == 'visserie':
            return o
    o = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    o.component.name = 'visserie'
    return o


def run_groups(names):
    d = design()
    root = d.rootComponent
    vocc = visserie_occ()
    looks = {'laiton': lib_appearance('Laiton poli', 'Prism-042'),
             'noir': lib_appearance('Oxyde noir', 'Prism-626')}
    log = []
    for gname in names:
        model, prefix, bname, r_mm, y_e, into, n, look = GROUPS[gname]
        edges = edges_for(prefix, bname, r_mm, ev(y_e))
        if len(edges) != n:
            raise RuntimeError('%s : %d arêtes trouvées au lieu de %d' % (gname, len(edges), n))
        df = app.data.findFileById(F[model])
        flips = 0
        for i, e in enumerate(edges):
            sub = vocc.component.occurrences.addByInsert(df, adsk.core.Matrix3D.create(), True)
            sub.isGroundToParent = False
            occ = sub.createForAssemblyContext(vocc)
            if look:
                occ.appearance = looks[look]
            def joint(flip):
                g1 = adsk.fusion.JointGeometry.createByPoint(
                    sub.component.originConstructionPoint.createForAssemblyContext(occ))
                g2 = adsk.fusion.JointGeometry.createByCurve(e, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
                ji = root.joints.createInput(g1, g2)
                ji.setAsRigidJointMotion()
                ji.isFlipped = flip
                j = root.joints.add(ji)
                j.name = '%s_%d' % (gname, i + 1)
                return j
            # isFlipped ne s'édite pas après coup : on recrée la liaison retournée si besoin.
            j = joint(False)
            o, x, y, z = occ.transform2.getAsCoordinateSystem()
            if z.y * into > 0:  # le +Z du modèle doit sortir du perçage
                j.deleteMe()
                j = joint(True)
                flips += 1
                o, x, y, z = occ.transform2.getAsCoordinateSystem()
            c = e.geometry.center
            if o.distanceTo(c) > 1e-4 or z.y * into > -0.999:
                raise RuntimeError('%s_%d mal placé : o=%s z=%s centre=%s' % (
                    gname, i + 1, [round(v * 10, 2) for v in o.asArray()], [round(v, 2) for v in z.asArray()],
                    [round(v * 10, 2) for v in c.asArray()]))
        log.append('%s : %d posés (%d retournés)' % (gname, n, flips))
    log.append('unhealthy %s' % unhealthy())
    txt = '\n'.join(log)
    open(os.path.join(os.environ['TEMP'], 'claudemetre', 'visserie.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


def run(ctx):
    run_groups(globals().get('GROUPS_TO_RUN', list(GROUPS)))
