# Plaquettes à texte fin : `epaisseur()` passe plaq_ep à 1,8 mm ; `hauteur()` passe plaq_H à 8 mm (4 mm de
# l'axe des vis à chaque bord, en haut et en bas comme sur les côtés) ; `texte()` remplace, dans chaque plaquette,
# le texte Barlow Condensed SemiBold 4,5 mm par le Barlow Semi Condensed Medium 3 mm des DXF
# (../../plaquettes/plaquettes_texte.py). Le reste de la plaquette, ses liaisons et ses vis ne bougent pas.
import adsk.core, adsk.fusion, os, json

P2 = os.path.join(os.path.dirname(__file__), 'plaquettes2.py')
_ns = {'__file__': P2}
exec(compile(open(P2, encoding='utf-8').read(), P2, 'exec'), _ns)
for _k in ('app', 'design', 'extrude', 'toward_wall', 'unhealthy', 'match_ink', 'CUT', 'NEW', 'DXF'):
    globals()[_k] = _ns[_k]
EP = '1.8 mm'
HAUT = '8 mm'
KEYS = ('session', 'semaine', 'reinit')


def epaisseur():
    d = design()
    d.userParameters.itemByName('plaq_ep').expression = EP
    print('plaq_ep', d.userParameters.itemByName('plaq_ep').expression, 'unhealthy', unhealthy())


def hauteur():
    d = design()
    d.userParameters.itemByName('plaq_H').expression = HAUT
    print('plaq_H', d.userParameters.itemByName('plaq_H').expression, 'unhealthy', unhealthy())


def _feature(coll, name):
    return next(f for f in coll if f.name == name)


def texte():
    d = design()
    root = d.rootComponent
    index = json.load(open(os.path.join(DXF, 'plaquettes.json'), encoding='utf-8'))['words']
    blanc = d.appearances.itemByName('PLA blanc')
    log = []
    for key in KEYS:
        occ = next(o for o in root.occurrences if o.component.name == 'plaquette_' + key)
        comp = occ.component
        body = comp.bRepBodies.itemByName('plaquette_' + key)
        vol0 = body.volume

        # 1. L'ancien texte : corps blancs, incrustation, esquisse.
        _feature(comp.features.extrudeFeatures, 'texte (1)').deleteMe()
        _feature(comp.features.extrudeFeatures, 'incrustation').deleteMe()
        comp.sketches.itemByName('texte').deleteMe()
        body = comp.bRepBodies.itemByName('plaquette_' + key)

        # 2. Le nouveau, comme plaquettes2.py : l'import sur un plan parallèle à XZ inverse l'axe vertical.
        occ.activate()
        face = comp.constructionPlanes.itemByName('plan_face')
        polys = index[key]['polys']
        opt = app.importManager.createDXF2DImportOptions(os.path.join(DXF, key + '_flip.dxf'), face)
        opt.isSingleSketchResult = True
        res = app.importManager.importToTarget2(opt, comp)
        tsk = [r for r in res if isinstance(r, adsk.fusion.Sketch)][0]
        ink, sign = match_ink(tsk, polys)
        if not ink or sign != 1:
            raise RuntimeError('texte %s non reconnu : %s %s' % (key, sign, len(polys)))
        tsk.name = 'texte'
        coll = adsk.core.ObjectCollection.create()
        for p in ink:
            coll.add(p)
        extrude(comp, coll, CUT, 'texte_p', toward_wall(comp), 'incrustation', [body])
        tf = extrude(comp, coll, NEW, 'texte_p', toward_wall(comp), 'texte')
        tbs = [tf.bodies.item(i) for i in range(tf.bodies.count)]
        for i, b in enumerate(tbs):
            b.name = 'texte_%s_%d' % (key, i + 1)
        d.activateRootComponent()
        for b in tbs:
            b.appearance = blanc
        xs = [v for b in tbs for v in (b.boundingBox.minPoint.x, b.boundingBox.maxPoint.x)]
        zs = [v for b in tbs for v in (b.boundingBox.minPoint.z, b.boundingBox.maxPoint.z)]
        log.append('%s : %d polygones, %d corps, x[%.2f, %.2f] z[%.2f, %.2f], plaquette %.1f -> %.1f mm3' % (
            key, len(ink), len(tbs), min(xs) * 10, max(xs) * 10, min(zs) * 10, max(zs) * 10, vol0 * 1000, body.volume * 1000))
    log.append('unhealthy %s' % unhealthy())
    print('\n'.join(log))
