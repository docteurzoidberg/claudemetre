# Plaque de flanc : dépassement et alignement sur les vis de platine, après plaque_encastree.py.
# saillie() : la plaque s'épaissit vers l'extérieur de plaque_saillie. La feuillure, les inserts et la
# liaison restent sur plaque_ep (partie logée dans la coque) : la coque ne change pas, et chaque plaque
# peut avoir son propre dépassement. alignement() : plaque_bord suit vis_z, pour que les vis de plaque
# soient à la même hauteur que celles de la platine (plaque de 86 au lieu de 88).
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

CIBLES = ('plaque (1)', 'plan_face', 'plaque_vis')


def etat(titre):
    d = design()
    root = d.rootComponent
    vals = {n: round(d.userParameters.itemByName(n).value * 10, 3) for n in
            ('plaque_H', 'plaque_bord', 'fen_H', 'pilier_z', 'flanc_vis_z', 'vis_z', 'plaque_ep')
            if d.userParameters.itemByName(n)}
    print(titre, vals)
    for o in root.occurrences:
        if o.component.name == 'plaque_flanc':
            b = o.boundingBox
            print(' ', o.name, 'x %.2f %.2f y %.2f %.2f z %.2f %.2f' % (
                b.minPoint.x * 10, b.maxPoint.x * 10, b.minPoint.y * 10, b.maxPoint.y * 10,
                b.minPoint.z * 10, b.maxPoint.z * 10))
    print('  alertes', unhealthy())


def saillie(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    if not d.userParameters.itemByName('plaque_saillie'):
        d.userParameters.add('plaque_saillie', adsk.core.ValueInput.createByString('1 mm'), 'mm',
                             'Plaque de flanc : dépassement de la face visible sur le flanc (0 = à fleur)')
    ep = d.userParameters.itemByName('plaque_ep')
    ep.comment = 'Plaque de flanc : épaisseur logée dans la feuillure'
    faits = []
    for q in list(ep.dependentParameters):
        c = q.createdBy if isinstance(q, adsk.fusion.ModelParameter) else None
        if c is not None and getattr(c, 'name', '') in CIBLES:
            q.expression = 'plaque_ep + plaque_saillie'
            faits.append(c.name)
    assert sorted(faits) == sorted(CIBLES), faits
    etat('saillie')


def alignement(ctx):
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name
    d = design()
    p = d.userParameters.itemByName('plaque_bord')
    p.expression = '( coque_H - 2 * coque_R ) / 2 - vis_z - plaque_vis_m'
    p.comment = 'Flanc : bord plat entre la plaque et l arrondi, tel que les vis de plaque soient à vis_z'
    etat('alignement')
