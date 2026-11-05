# Interférences visserie <-> pièces, regroupées par type de paire (volume total, nombre).
import adsk.core, adsk.fusion, os


def run(ctx):
    app = adsk.core.Application.get()
    d = adsk.fusion.Design.cast(app.activeProduct)
    root = d.rootComponent
    ents = []
    for occ in root.occurrences:
        if occ.component.name == 'visserie':
            for sub in occ.childOccurrences:
                for b in sub.bRepBodies:
                    ents.append((sub.component.name, b))
        else:
            for b in occ.bRepBodies:
                if occ.component.name.startswith('afficheur') and b.name != 'Body16':
                    continue
                if occ.component.name.startswith('voltmetre') and b.name != 'Body1':
                    continue
                ents.append((occ.component.name, b))
    coll = adsk.core.ObjectCollection.create()
    for _, b in ents:
        coll.add(b)
    res = d.analyzeInterference(d.createInterferenceInput(coll))

    def inside(b, p, tol=0.01):
        bb = b.boundingBox
        return all(lo - tol <= v <= hi + tol for lo, v, hi in
                   zip(bb.minPoint.asArray(), p.asArray(), bb.maxPoint.asArray()))

    agg = {}
    for r in res:
        bb = r.interferenceBody.boundingBox
        c = adsk.core.Point3D.create(*[(a + b) / 2 for a, b in zip(bb.minPoint.asArray(), bb.maxPoint.asArray())])
        names = sorted({n for n, b in ents if inside(b, c)})
        k = tuple(names) + (('y=%.1f' % (c.y * 10)),) if len(names) != 2 else tuple(names)
        a = agg.setdefault(k, [0, 0.0])
        a[0] += 1
        a[1] += r.interferenceBody.volume * 1000
    out = ['%s <-> %s : %d paires, %.2f mm3' % (k[0], k[1], v[0], v[1]) for k, v in sorted(agg.items())]
    txt = '\n'.join(out) or 'aucune interference'
    open(os.path.join(os.environ['TEMP'], 'claudemetre', 'check_visserie.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)
