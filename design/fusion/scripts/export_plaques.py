"""Export des plaques de flanc, relançable : un STL binaire en mm par plaque, en repère du
composant (à plat sur XY, face d'appui à z = 0, face visible vers +Z), et plaques.json (volumes, cotes),
dans %TEMP%/claudemetre/export/plaques/. La hauteur de chaque plaque est mesurée sur son corps : toutes
n'ont pas de paramètre de saillie. Exporte le design ouvert tel quel, signale s'il n'est pas enregistré.
Ensuite, côté WSL : uv run plaques_3mf.py (design/fusion) écrit les 3MF."""
import json
import os
import adsk.core, adsk.fusion

KEYS = ('plaque_flanc', 'plaque_bossage', 'plaque_bossage_fusible')


def run(ctx):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    assert doc.name.startswith('claudometre'), doc.name
    d = adsk.fusion.Design.cast(app.activeProduct)
    tl = d.timeline
    bad = [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != 0]
    if bad:
        raise RuntimeError('fonctions en erreur %s' % bad)
    out = os.path.join(os.environ['TEMP'], 'claudemetre', 'export', 'plaques')
    os.makedirs(out, exist_ok=True)
    em = d.exportManager
    up = d.userParameters
    info = {'non_enregistre': doc.isModified, 'version': doc.dataFile.versionNumber if doc.dataFile else None,
            'plaques': {}}
    for n in ('plaque_P', 'plaque_H', 'fen_P'):
        info[n] = round(up.itemByName(n).value * 10, 3)
    for key in KEYS:
        comp = next(o for o in d.rootComponent.occurrences if o.component.name == key).component
        assert comp.bRepBodies.count == 1, (key, comp.bRepBodies.count)
        body = comp.bRepBodies.item(0)
        f = key + '.stl'
        opt = em.createSTLExportOptions(body, os.path.join(out, f))
        opt.isBinaryFormat = True
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        opt.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        em.execute(opt)
        bb = body.boundingBox
        info['plaques'][key] = {'stl': f, 'volume': round(body.volume * 1000, 3),
                                'hauteur': round((bb.maxPoint.z - bb.minPoint.z) * 10, 3),
                                'apparence': body.appearance.name if body.appearance else None}
    with open(os.path.join(out, 'plaques.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    print(info)
