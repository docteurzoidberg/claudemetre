# Sonde, lecture seule : texte des plaquettes (position, couleur), tête des vis, ce qu'il y a derrière leur pointe.
import adsk.core, adsk.fusion, json, os


def run(ctx):
    app = adsk.core.Application.get()
    d = adsk.fusion.Design.cast(app.activeProduct)
    root = d.rootComponent
    words = json.load(open(os.path.join(os.path.dirname(__file__), 'dxf', 'plaquettes.json'), encoding='utf-8'))['words']
    out = []
    for occ in root.occurrences:
        c = occ.component
        if not c.name.startswith('plaquette_'):
            continue
        key = c.name.split('_')[1]
        pb = [b for b in occ.bRepBodies if b.name == c.name][0]
        tb = [b for b in occ.bRepBodies if b.name.startswith('texte_')]
        bb = pb.boundingBox
        xs = [v for b in tb for v in (b.boundingBox.minPoint.x, b.boundingBox.maxPoint.x)]
        zs = [v for b in tb for v in (b.boundingBox.minPoint.z, b.boundingBox.maxPoint.z)]
        ys = [v for b in tb for v in (b.boundingBox.minPoint.y, b.boundingBox.maxPoint.y)]
        cx = (bb.minPoint.x + bb.maxPoint.x) / 2
        cz = (bb.minPoint.z + bb.maxPoint.z) / 2
        out.append('%s plaque x %.2f..%.2f z %.2f..%.2f y %.2f..%.2f (ép %.2f) vol %.1f | texte larg %.2f (dxf %.2f) dx %.2f, z rel %.2f..%.2f, y %.2f..%.2f, couleurs %s/%s' % (
            key, bb.minPoint.x * 10, bb.maxPoint.x * 10, bb.minPoint.z * 10, bb.maxPoint.z * 10, bb.minPoint.y * 10, bb.maxPoint.y * 10,
            (bb.maxPoint.y - bb.minPoint.y) * 10, pb.volume * 1000, (max(xs) - min(xs)) * 10, words[key]['width'], ((max(xs) + min(xs)) / 2 - cx) * 10,
            (min(zs) - cz) * 10, (max(zs) - cz) * 10, min(ys) * 10, max(ys) * 10,
            pb.appearance.name if pb.appearance else None, sorted({b.appearance.name for b in tb if b.appearance})))
    vis = next(o for o in root.occurrences if o.component.name == 'visserie')
    for j in root.joints:
        if not j.name.startswith('vis_plaquettes_'):
            continue
        o = j.occurrenceOne
        o = o if o.component.name.startswith('vis_') else j.occurrenceTwo
        bb = o.boundingBox
        c = adsk.core.Point3D.create((bb.minPoint.x + bb.maxPoint.x) / 2, bb.maxPoint.y + 0.001, (bb.minPoint.z + bb.maxPoint.z) / 2)
        hits = adsk.core.ObjectCollection.create()
        pts = adsk.core.ObjectCollection.create()
        res = root.findBRepUsingRay(c, adsk.core.Vector3D.create(0, 1, 0), adsk.fusion.BRepEntityTypes.BRepBodyEntityType, -1.0, True, pts)
        first = []
        for i in range(min(res.count, 3)):
            b = res.item(i)
            first.append('%s/%s à %.1f' % (b.assemblyContext.name if b.assemblyContext else '?', b.name, (pts.item(i).y - c.y) * 10))
        out.append('%s tête y %.2f pointe y %.2f x %.1f z %.1f -> %s' % (j.name, bb.minPoint.y * 10, bb.maxPoint.y * 10, c.x * 10, c.z * 10, first))
    txt = '\n'.join(out)
    open(os.path.join(os.path.dirname(__file__), 'check_plaquettes.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)
