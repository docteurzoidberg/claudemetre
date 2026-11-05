"""Export de la visière, relançable : STL binaire en mm et visiere.json (volume, cotes)
dans %TEMP%/claudemetre/export/. Exporte le design ouvert tel quel, signale s'il n'est pas
enregistré. Ensuite, côté WSL : uv run visiere_3mf.py (design/fusion) écrit le 3MF."""
import json
import os
import adsk.core, adsk.fusion


def run(ctx):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    assert doc.name.startswith('claudometre'), doc.name
    d = adsk.fusion.Design.cast(app.activeProduct)
    tl = d.timeline
    bad = [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != 0]
    if bad:
        raise RuntimeError('fonctions en erreur %s' % bad)
    occ = [o for o in d.rootComponent.occurrences if o.component.name == 'visiere'][0]
    assert occ.component.bRepBodies.count == 1, occ.component.bRepBodies.count
    body = occ.component.bRepBodies.item(0)
    out = os.path.join(os.environ['TEMP'], 'claudemetre', 'export')
    os.makedirs(out, exist_ok=True)
    em = d.exportManager
    opt = em.createSTLExportOptions(occ, os.path.join(out, 'visiere.stl'))
    opt.isBinaryFormat = True
    opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    opt.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    em.execute(opt)
    up = d.userParameters
    info = {'volume': round(body.volume * 1000, 3), 'non_enregistre': doc.isModified,
            'version': doc.dataFile.versionNumber if doc.dataFile else None}
    for n in ('visiere_L', 'visiere_P', 'visiere_dz_haut', 'visiere_dz_bas', 'rainure_p'):
        info[n] = round(up.itemByName(n).value * 10, 3)
    with open(os.path.join(out, 'visiere.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    print(info)
