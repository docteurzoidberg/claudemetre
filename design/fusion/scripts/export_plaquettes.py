"""Export des plaquettes, relançable : un STL binaire en mm par corps (plaquette et
lettres), en repère du design, et export.json (volumes, cotes), dans
%TEMP%/claudemetre/export/plaquettes/. Exporte le design ouvert tel quel, signale s'il n'est pas
enregistré. Ensuite, côté WSL : uv run plaquettes_3mf.py (design/fusion) écrit le 3MF."""
import json
import os
import shutil
import adsk.core, adsk.fusion

KEYS = ('session', 'semaine', 'reinit')


def run(ctx):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    assert doc.name.startswith('claudometre'), doc.name
    d = adsk.fusion.Design.cast(app.activeProduct)
    tl = d.timeline
    bad = [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != 0]
    if bad:
        raise RuntimeError('fonctions en erreur %s' % bad)
    out = os.path.join(os.environ['TEMP'], 'claudemetre', 'export', 'plaquettes')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    em = d.exportManager
    up = d.userParameters
    info = {'non_enregistre': doc.isModified, 'version': doc.dataFile.versionNumber if doc.dataFile else None,
            'plaquettes': {}}
    for n in ('plaq_L', 'plaq_H', 'plaq_ep', 'texte_p'):
        info[n] = round(up.itemByName(n).value * 10, 3)
    for key in KEYS:
        occ = next(o for o in d.rootComponent.occurrences if o.component.name == 'plaquette_' + key)
        e = info['plaquettes'][key] = {'noir': None, 'blanc': []}
        for b in occ.bRepBodies:
            f = b.name + '.stl'
            opt = em.createSTLExportOptions(b, os.path.join(out, f))
            opt.isBinaryFormat = True
            opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            opt.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
            em.execute(opt)
            row = {'stl': f, 'volume': round(b.volume * 1000, 3)}
            if b.name == 'plaquette_' + key:
                e['noir'] = row
            else:
                e['blanc'].append(row)
    with open(os.path.join(out, 'export.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    print({k: (len(v['blanc']), v['noir']['volume']) for k, v in info['plaquettes'].items()}, info['version'], info['non_enregistre'])
