# Sonde de plaque_bossage. run() : interférences et jeux du connecteur posé, lecture seule.
# essai_usbc() : pose le LP-16 USB-C à la place du 2 pôles, mesure, puis lève une exception pour que Fusion
# annule tout (le rapport est dans le message d'erreur et dans %TEMP%\claudemetre\check_bossage.txt).
import adsk.core, adsk.fusion, os

app = adsk.core.Application.get()
HERE = os.path.dirname(__file__)


def rapport():
    d = adsk.fusion.Design.cast(app.activeProduct)
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    root = d.rootComponent
    occs = {o.name: o for o in root.occurrences}
    plaque = [o for o in root.occurrences if o.component.name == 'plaque_bossage'][0]
    lp = [o for o in plaque.childOccurrences if o.component.name.startswith('connecteur_LP-16') and o.isLightBulbOn][0]
    kaki = [b for b in plaque.bRepBodies if b.name == 'plaque_bossage'][0]
    coque = occs['coque:1'].bRepBodies.item(0)
    vis = [s for s in list(occs['visserie:1'].childOccurrences) + list(plaque.childOccurrences)
           if s.component.name in ('vis_CHC_M3x6', 'vis_FHC_M3x12') and s.transform2.translation.x > 9]
    so45 = list(occs['voltmetre_SO-45:1'].bRepBodies)
    out = []

    corps = list(lp.bRepBodies)
    bb = [b.boundingBox for b in corps]
    out.append('%s : x min %.2f x max %.2f, z min %.2f z max %.2f' % (
        lp.component.name, min(b.minPoint.x for b in bb) * 10, max(b.maxPoint.x for b in bb) * 10,
        min(b.minPoint.z for b in bb) * 10, max(b.maxPoint.z for b in bb) * 10))

    mm = app.measureManager
    for nom, cible in (('plaque', kaki), ('coque', coque)):
        v = min(mm.measureMinimumDistance(b, cible).value for b in corps) * 10
        out.append('jeu connecteur / %s : %.2f' % (nom, v))
    v = min(mm.measureMinimumDistance(b, c).value for b in corps for c in so45) * 10
    out.append('jeu connecteur / SO-45 : %.2f' % v)
    v = min(mm.measureMinimumDistance(kaki, c).value for c in so45) * 10
    out.append('jeu plaque / SO-45 : %.2f' % v)
    fhc = [b for s in vis if s.component.name == 'vis_FHC_M3x12' for b in s.bRepBodies]
    if fhc:
        arriere = [b for b in corps if b.boundingBox.minPoint.x < plaque.bRepBodies.item(0).boundingBox.minPoint.x + 1.5]
        out.append('jeu FHC / arrière du connecteur : %.2f' % (min(mm.measureMinimumDistance(a, b).value for a in fhc for b in arriere) * 10))
        out.append('jeu FHC / coque : %.2f' % (min(mm.measureMinimumDistance(a, coque).value for a in fhc) * 10))
        out.append('jeu FHC / SO-45 : %.2f' % (min(mm.measureMinimumDistance(a, c).value for a in fhc for c in so45) * 10))

    coll = adsk.core.ObjectCollection.create()
    nommes = [('plaque', kaki), ('coque', coque)]
    nommes += [('connecteur', b) for b in corps]
    nommes += [('vis', b) for s in vis for b in s.bRepBodies]
    for _, b in nommes:
        coll.add(b)
    res = d.analyzeInterference(d.createInterferenceInput(coll))

    def dedans(b, p):
        q = b.boundingBox
        return all(lo - 0.01 <= c <= hi + 0.01 for lo, c, hi in zip(q.minPoint.asArray(), p.asArray(), q.maxPoint.asArray()))

    agg = {}
    for r in res:
        q = r.interferenceBody.boundingBox
        c = adsk.core.Point3D.create(*[(a + b) / 2 for a, b in zip(q.minPoint.asArray(), q.maxPoint.asArray())])
        k = ' / '.join(sorted({n for n, b in nommes if dedans(b, c)}))
        a = agg.setdefault(k, [0, 0.0, None])
        a[0] += 1
        a[1] += r.interferenceBody.volume * 1000
        a[2] = [round(v * 10, 1) for v in c.asArray()]
    out.append('interférences : %d' % res.count)
    for k, (n, v, c) in sorted(agg.items()):
        out.append('  %s : %d, %.3f mm3, vers %s' % (k, n, v, c))
    # Le modèle STEP se chevauche lui-même : ce qui reste, connecteur seul, ne concerne pas la plaque.
    seul = adsk.core.ObjectCollection.create()
    for b in corps:
        seul.add(b)
    r2 = d.analyzeInterference(d.createInterferenceInput(seul))
    out.append('connecteur seul : %d, %.3f mm3' % (r2.count, sum(r.interferenceBody.volume for r in r2) * 1000))
    txt = '\n'.join(out)
    open(os.path.join(os.environ['TEMP'], 'claudemetre', 'check_bossage.txt'), 'w', encoding='utf-8').write(txt)
    return txt


def run(ctx):
    print(rapport())


def essai_usbc(ctx):
    p = os.path.join(HERE, 'plaque_bossage.py')
    ns = {'__file__': p}
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), ns)
    d = adsk.fusion.Design.cast(app.activeProduct)
    root = d.rootComponent
    plaque = [o for o in root.occurrences if o.component.name == 'plaque_bossage'][0]
    deux = [o for o in plaque.childOccurrences if o.component.name == 'connecteur_LP-16_2poles'][0]
    deux.isLightBulbOn = False
    ns['pose_connecteur'](ctx, 'connecteur_LP-16_USB-C')
    raise RuntimeError('ESSAI ANNULÉ\n' + rapport())
