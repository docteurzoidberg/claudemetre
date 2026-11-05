# Sonde : trous de serrure de la coque. positions() et chemin() sont en lecture seule ;
# essai() change la tête et la tige pour vérifier que tout suit, puis remet les valeurs d'origine.
import adsk.core, adsk.fusion

app = adsk.core.Application.get()
P3 = adsk.core.Point3D.create
V3 = adsk.core.Vector3D.create


def des():
    return adsk.fusion.Design.cast(app.activeProduct)


def coque():
    return [o for o in des().rootComponent.occurrences if o.component.name == 'coque'][0].component.bRepBodies.item(0)


def positions():
    """Faces cylindriques du fond dans l'axe des jauges : (x, z, diamètre), en mm."""
    out = []
    for f in coque().faces:
        g = f.geometry
        if isinstance(g, adsk.core.Cylinder) and abs(g.axis.y) > 0.99 and 4.0 < abs(g.origin.x) < 7.5 and f.boundingBox.minPoint.y > 3.6:
            out.append((round(g.origin.x * 10, 2), round(g.origin.z * 10, 2), round(g.radius * 20, 2)))
    return sorted(set(out))


def bodies(occ):
    out = list(occ.bRepBodies)
    for c in occ.childOccurrences:
        out += bodies(c)
    return out


def chemin(ctx):
    """Corps de l'assemblage qui entrent dans un pavé couvrant le chemin de la tête, derrière le fond."""
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = des()
    ev = lambda e: d.unitsManager.evaluateExpression(e, 'mm')
    tm = adsk.fusion.TemporaryBRepManager.get()
    print('positions', positions())
    x, zh = ev('accroche_x'), ev('accroche_z')
    zb = zh - ev('accroche_course')
    r = 0.7                     # tête jusqu'à 14 mm
    y1 = ev('coque_P - coque_fond')
    tous = [b for o in d.rootComponent.occurrences if o.component.name != 'coque' for b in bodies(o)]
    print('corps testés', len(tous))
    for prof in (0.4, 0.7, 1.0, 1.5):
        y0 = y1 - prof
        for s in (1, -1):
            c = P3(s * x, (y0 + y1) / 2, (zb + zh) / 2)
            box = adsk.core.OrientedBoundingBox3D.create(c, V3(1, 0, 0), V3(0, 1, 0), 2 * r, prof, zh - zb + 2 * r)
            lo = (s * x - r, y0, zb - r)
            hi = (s * x + r, y1, zh + r)
            hits = []
            for b in tous:
                bb = b.boundingBox
                a, e = bb.minPoint.asArray(), bb.maxPoint.asArray()
                if all(a[i] < hi[i] and e[i] > lo[i] for i in range(3)):
                    t, u = tm.createBox(box), tm.copy(b)
                    try:
                        tm.booleanOperation(t, u, adsk.fusion.BooleanTypes.IntersectionBooleanType)
                        v = t.volume * 1000
                    except Exception:
                        v = 0.0
                    if v > 1e-3:
                        ac = b.assemblyContext
                        hits.append('%s/%s %.1f mm3' % (ac.name if ac else '', b.name, v))
            print('profondeur', prof * 10, 'côté', s, 'collisions', hits)


def essai(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = des()
    up = d.userParameters
    t, g = up.itemByName('accroche_tete_d'), up.itemByName('accroche_tige_d')
    t0, g0 = t.expression, g.expression
    v0 = coque().volume
    for a, b in (('11 mm', '5 mm'), ('5 mm', '2.5 mm')):
        t.expression, g.expression = a, b
        print('tête', a, 'tige', b, 'course', round(up.itemByName('accroche_course').value * 10, 2), positions(),
              'volume', round(coque().volume * 1000, 1))
    t.expression, g.expression = t0, g0
    bad = [(d.timeline.item(i).name, d.timeline.item(i).errorOrWarningMessage) for i in range(d.timeline.count)
           if d.timeline.item(i).healthState != 0]
    print('remis', t.expression, g.expression, positions(), 'écart volume', round((coque().volume - v0) * 1000, 3), 'en erreur', bad)
