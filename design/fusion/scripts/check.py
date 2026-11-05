# Jeux entre pièces : distance minimale des paires proches (boîtes englobantes à moins de MARGE),
# puis volume d'interférence des paires en contact. Résultat aussi écrit dans check.txt.
import adsk.core, adsk.fusion, os

MARGE = 0.15  # cm


def run(ctx):
    app = adsk.core.Application.get()
    d = adsk.fusion.Design.cast(app.activeProduct)
    root = d.rootComponent
    items = []
    for occ in root.occurrences:
        for b in occ.bRepBodies:
            if b.isLightBulbOn and b.isVisible:
                items.append((occ.name, b))

    def near(b1, b2):
        a, c = b1.boundingBox, b2.boundingBox
        for i in range(3):
            if a.minPoint.asArray()[i] > c.maxPoint.asArray()[i] + MARGE:
                return False
            if c.minPoint.asArray()[i] > a.maxPoint.asArray()[i] + MARGE:
                return False
        return True

    mm = app.measureManager
    out, contact = [], []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (o1, b1), (o2, b2) = items[i], items[j]
            if o1 == o2 or not near(b1, b2):
                continue
            dist = mm.measureMinimumDistance(b1, b2).value * 10
            if dist < MARGE * 10:
                out.append('%-22s %-8s | %-22s %-8s : %.2f mm' % (o1, b1.name, o2, b2.name, dist))
                if dist < 1e-3:
                    contact.append((b1, b2, '%s/%s - %s/%s' % (o1, b1.name, o2, b2.name)))
    for b1, b2, lab in contact:
        coll = adsk.core.ObjectCollection.create()
        coll.add(b1)
        coll.add(b2)
        res = d.analyzeInterference(d.createInterferenceInput(coll))
        vol = sum(r.interferenceBody.volume for r in res) * 1000 if res else 0.0
        out.append('interference %s : %.3f mm3' % (lab, vol))
    txt = '\n'.join(out)
    open(os.path.join(os.environ['TEMP'], 'claudemetre', 'check.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)
