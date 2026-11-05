# Sonde, lecture seule : jeux et collisions de la carte à borniers et des clips
# avec le reste de l'assemblage. Boîtes englobantes pour trier, puis mesure exacte sur les
# paires proches ; les collisions se vérifient par intersection de copies temporaires.
import adsk.core, adsk.fusion, os, time

app = adsk.core.Application.get()


def box(b):
    bb = b.boundingBox
    return (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)


def gap(a, b):
    d = [max(a[i] - b[i + 3], b[i] - a[i + 3], 0.0) for i in range(3)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def bodies(occ):
    out = list(occ.bRepBodies)
    for c in occ.childOccurrences:
        out += bodies(c)
    return out


def label(b):
    a = b.assemblyContext
    return (a.name if a else '') + '/' + b.name


def inter(tm, a, b):
    ta, tb = tm.copy(a), tm.copy(b)
    try:
        tm.booleanOperation(ta, tb, adsk.fusion.BooleanTypes.IntersectionBooleanType)
        return ta.volume * 1000
    except Exception:
        return 0.0


def run(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    t0 = time.time()
    d = adsk.fusion.Design.cast(app.activeProduct)
    r = d.rootComponent
    tm = adsk.fusion.TemporaryBRepManager.get()
    mm = app.measureManager
    occ = {o.name: o for o in r.occurrences}
    carte = [(b, box(b)) for b in bodies(occ['mrd076a_esp32_s3:1'])]
    clips = [(b, box(b)) for n in ('clip_aile:1', 'clip_aile_miroir:1', 'clip_milieu:1') for b in bodies(occ[n])]
    print('corps carte', len(carte), 'clips', len(clips))

    # 1. Clips contre carte : collisions
    tot = 0
    for cb, cx in clips:
        near = [(b, x) for b, x in carte if gap(cx, x) < 1e-6]
        for b, x in near:
            v = inter(tm, cb, b)
            if v > 1e-4:
                tot += 1
                print('COLLISION', label(cb), label(b), 'vol %.3f mm3' % v,
                      'zone', [round(c * 10, 2) for c in x])
        print(label(cb), 'paires en contact de boîte', len(near))
    print('collisions clips/carte', tot, 't', round(time.time() - t0, 1))

    # 2. Carte + clips contre les voisins : plus petits jeux
    voisins = ('coque:1', 'voltmetre_SO-45:1', 'voltmetre_SO-45:2', 'afficheur_TM1637_056:1', 'claude:1',
               'platine:1', 'plaque_flanc:1', 'plaque_flanc:2', 'visserie:1')
    moi = carte + clips
    for n in voisins:
        vb = [(b, box(b)) for b in bodies(occ[n])]
        pairs = []
        for b, x in moi:
            for v, y in vb:
                g = gap(x, y)
                if g < 0.6:
                    pairs.append((g, b, v))
        pairs.sort(key=lambda p: p[0])
        best = None
        for g, b, v in pairs[:25]:
            if best is not None and g * 10 > best[0]:
                break
            m = mm.measureMinimumDistance(b, v).value * 10
            if best is None or m < best[0]:
                best = (m, label(b), label(v))
        print(n, 'paires', len(pairs), 'jeu', ('%.2f mm %s <> %s' % (best[0], best[1][:44], best[2][:30])) if best else '> 6 mm',
              't', round(time.time() - t0, 1))
        if time.time() - t0 > 100:
            print('arret temps')
            break
