"""Export du patron de perçage, relançable : STL binaire en mm et patron.json (volume,
position, cotes des vis) dans %TEMP%/claudemetre/export/. Exporte le design ouvert tel quel, même
non enregistré. Ensuite, côté WSL : uv run patron_3mf.py (design/fusion) écrit le 3MF."""
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
    occ = [o for o in d.rootComponent.occurrences if o.component.name == 'patron'][0]
    body = occ.component.bRepBodies.item(0)
    out = os.path.join(os.environ['TEMP'], 'claudemetre', 'export')
    os.makedirs(out, exist_ok=True)
    em = d.exportManager
    opt = em.createSTLExportOptions(occ, os.path.join(out, 'patron.stl'))
    opt.isBinaryFormat = True
    opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    opt.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    em.execute(opt)
    up = d.userParameters
    mm = lambda n: round(up.itemByName(n).value * 10, 3)
    info = {'volume': round(body.volume * 1000, 3), 'non_enregistre': doc.isModified,
            'version': doc.dataFile.versionNumber if doc.dataFile else None}
    for n in ('patron_y', 'patron_ep', 'patron_trou_d', 'patron_z', 'accroche_x', 'accroche_course',
              'accroche_tete_d', 'accroche_tige_d', 'coque_L', 'coque_H'):
        info[n] = mm(n)
    with open(os.path.join(out, 'patron.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    print(info)
