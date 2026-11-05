# Étape 3 : plaquettes reconstruites centrées sur leur origine, placées par liaison (suivent les
# paramètres), texte Barlow Condensed SemiBold incrusté (corps « texte » séparé, multi-filament).
import adsk.core, adsk.fusion, os, json

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))
VIS = os.path.join(os.path.dirname(__file__), 'visserie.py')
DXF = os.path.join(os.path.dirname(__file__), 'dxf')
APP_LIB = 'BA5EE55E-9982-449B-9D66-9F036540E140'

PLAQ = {
    'session': ('-jauge_x', 'jauge_z - plaq_jauge_dz'),
    'semaine': ('jauge_x', 'jauge_z - plaq_jauge_dz'),
    'reinit': ('aff_x', 'aff_z - plaq_aff_dz'),
}


def appearance(name, src_id, rgb):
    d = design()
    a = d.appearances.itemByName(name)
    if a:
        return a
    a = d.appearances.addByCopy(app.materialLibraries.itemById(APP_LIB).appearances.itemById(src_id), name)
    for i in range(a.appearanceProperties.count):
        p = a.appearanceProperties.item(i)
        if isinstance(p, adsk.core.ColorProperty) and p.id in ('opaque_albedo', 'generic_diffuse'):
            p.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
    return a


def is_corner_edge(e, L, H):
    g = e.geometry
    if not isinstance(g, adsk.core.Line3D):
        return False
    a, b = e.startVertex.geometry, e.endVertex.geometry
    if abs(a.x - b.x) > 1e-4 or abs(a.z - b.z) > 1e-4:
        return False
    return abs(abs(a.x) - L / 2) < 1e-3 and abs(abs(a.z) - H / 2) < 1e-3


def match_ink(sk, polys):
    """Profils d'encre : un par polygone du JSON (aire et centre, x et z modèle en mm).
    Renvoie (profils, sens) ou (None, info) si rien ne correspond."""
    info = []
    for sign in (1, -1):
        found = []
        for q in polys:
            best = None
            for i in range(sk.profiles.count):
                p = sk.profiles.item(i)
                ap = p.areaProperties()
                if abs(ap.area * 100 - q['area']) > 0.02 * q['area'] + 0.01:
                    continue
                # centre en repère modèle (selon les versions, centroid est déjà en repère modèle)
                for c in (ap.centroid, sk.sketchToModelSpace(ap.centroid)):
                    if abs(c.x * 10 - q['cx']) < 0.05 and abs(c.z * 10 - sign * q['cy']) < 0.05:
                        best = p
            if best is None:
                break
            found.append(best)
        if len(found) == len(polys):
            return found, sign
        info.append('sign %d: %d/%d' % (sign, len(found), len(polys)))
    return None, '; '.join(info)


def run(ctx):
    d = design()
    root = d.rootComponent
    set_params([('texte_p', '0.6 mm', 'Plaquettes : profondeur du texte incrusté (3 couches de 0,2)')])
    noir = d.appearances.itemByName('PLA noir')
    blanc = appearance('PLA blanc', 'Prism-127', (236, 234, 226))
    index = json.load(open(os.path.join(DXF, 'plaquettes.json'), encoding='utf-8'))['words']
    log = []

    # 1. Supprimer les vis de plaquettes (liaisons + occurrences) puis les anciennes plaquettes.
    for i in range(1, 7):
        j = root.joints.itemByName('vis_plaquettes_%d' % i)
        if j:
            occ = j.occurrenceOne
            j.deleteMe()
            (occ.nativeObject or occ).deleteMe()
    for o in [o for o in root.occurrences if o.component.name.startswith('plaquette_')]:
        o.deleteMe()

    # 2. Reconstruire chaque plaquette autour de son origine.
    for key, (x_e, z_e) in PLAQ.items():
        occ = new_component('plaquette_' + key)
        occ.isGroundToParent = False
        comp = occ.component
        occ.activate()
        sk = sketch(comp, comp.xZConstructionPlane, 'plaquette')
        centered_rect(sk, 'plaq_L', 'plaq_H')
        body = extrude(comp, sk.profiles.item(0), NEW, 'plaq_ep', toward_front(comp), 'plaquette').bodies.item(0)
        body.name = 'plaquette_' + key
        fillet(comp, [e for e in body.edges if is_corner_edge(e, ev('plaq_L'), ev('plaq_H'))], 'plaq_R', 'coins')
        face = plane_y(comp, '-plaq_ep', 'plan_face')
        sk = sketch(comp, face, 'vis')
        pts = two_points(sk, sk.originPoint, 0, 0, 'plaq_vis_e / 2')
        hole(comp, pts, 'fraise', 'vis_d', 'plaq_ep', True, 'vis', [body], csk_d='fraise_d')

        polys = index[key]['polys']
        ink, sign = None, None
        # L'import DXF sur un plan parallèle à XZ inverse l'axe vertical : le DXF retourné d'abord.
        for suffix in ('_flip', ''):
            opt = app.importManager.createDXF2DImportOptions(os.path.join(DXF, key + suffix + '.dxf'), face)
            opt.isSingleSketchResult = True
            res = app.importManager.importToTarget2(opt, comp)
            tsk = [r for r in res if isinstance(r, adsk.fusion.Sketch)][0]
            ink, sign = match_ink(tsk, polys)
            if ink and sign == 1:
                tsk.name = 'texte'
                break
            tsk.deleteMe()
            log.append('%s%s : %s' % (key, suffix, sign))
            ink = None
        if not ink:
            raise RuntimeError('texte %s non reconnu : %s' % (key, ' | '.join(log)))
        coll = adsk.core.ObjectCollection.create()
        for p in ink:
            coll.add(p)
        extrude(comp, coll, CUT, 'texte_p', toward_wall(comp), 'incrustation', [body])
        tf = extrude(comp, coll, NEW, 'texte_p', toward_wall(comp), 'texte')
        tbs = [tf.bodies.item(i) for i in range(tf.bodies.count)]    # un corps par lettre
        for i, b in enumerate(tbs):
            b.name = 'texte_%s_%d' % (key, i + 1)
        d.activateRootComponent()
        body.appearance = noir
        for b in tbs:
            b.appearance = blanc

        jo = root.jointOrigins.itemByName('jo_plaquette_' + key)
        if jo is None:
            inp = root.jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(root.originConstructionPoint))
            inp.offsetX = VI(x_e)
            inp.offsetY = VI('-platine_ep')
            inp.offsetZ = VI(z_e)
            jo = root.jointOrigins.add(inp)
            jo.name = 'jo_plaquette_' + key
        ji = root.joints.createInput(adsk.fusion.JointGeometry.createByPoint(
            comp.originConstructionPoint.createForAssemblyContext(occ)), jo)
        ji.setAsRigidJointMotion()
        root.joints.add(ji).name = 'plaquette_' + key
        o, x, y, z = occ.transform2.getAsCoordinateSystem()
        want = (ev(x_e), ev('-platine_ep'), ev(z_e))
        if o.distanceTo(adsk.core.Point3D.create(*want)) > 1e-4 or x.x < 0.999 or z.z < 0.999:
            raise RuntimeError('plaquette %s mal placée : %s' % (key, [round(v * 10, 2) for v in o.asArray()]))
        xs = [v for b in tbs for v in (b.boundingBox.minPoint.x, b.boundingBox.maxPoint.x)]
        zs = [v for b in tbs for v in (b.boundingBox.minPoint.z, b.boundingBox.maxPoint.z)]
        log.append('%s : %d polygones, %d corps de texte, x[%.1f, %.1f] z[%.1f, %.1f] (repère local)' % (
            key, len(ink), len(tbs), min(xs) * 10, max(xs) * 10, min(zs) * 10, max(zs) * 10))

    # 3. Remettre les vis de plaquettes.
    ns = {'__file__': VIS}
    exec(compile(open(VIS, encoding='utf-8').read(), VIS, 'exec'), ns)
    ns['run_groups'](['vis_plaquettes'])
    log.append('unhealthy %s' % unhealthy())
    print('\n'.join(log))
