"""Export des clips du support de carte, relançable : un STL binaire en mm par clip, en
repère du composant (base à z = 0, grand crochet vers +X), et clips.json (volumes, cotes), dans
%TEMP%/claudemetre/export/clips/. Exporte le design ouvert tel quel, signale s'il n'est pas
enregistré. Ensuite, côté WSL : uv run clips_3mf.py (design/fusion) écrit le 3MF."""
import json
import os
import adsk.core, adsk.fusion

KEYS = ('clip_aile', 'clip_aile_miroir', 'clip_milieu')


def run(ctx):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    assert doc.name.startswith('claudometre'), doc.name
    d = adsk.fusion.Design.cast(app.activeProduct)
    tl = d.timeline
    bad = [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != 0]
    if bad:
        raise RuntimeError('fonctions en erreur %s' % bad)
    out = os.path.join(os.environ['TEMP'], 'claudemetre', 'export', 'clips')
    os.makedirs(out, exist_ok=True)
    em = d.exportManager
    up = d.userParameters
    info = {'non_enregistre': doc.isModified, 'version': doc.dataFile.versionNumber if doc.dataFile else None,
            'clips': {}}
    for n in ('clip_L', 'clip_aile_l', 'clip_mil_l'):
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
        info['clips'][key] = {'stl': f, 'volume': round(body.volume * 1000, 3)}
    with open(os.path.join(out, 'clips.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    print(info)
