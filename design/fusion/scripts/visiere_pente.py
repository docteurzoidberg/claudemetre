# Pente de la visière : l'avant des joues est incliné, de visiere_P sous le toit à visiere_P_bas en bas.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))


def run(ctx):
    d = design()
    set_params([('visiere_P_bas', '4 mm', 'Visière : saillie des joues en bas (pente de l avant des joues)')])
    occ = [o for o in d.rootComponent.occurrences if o.component.name == 'visiere'][0]
    comp = occ.component
    body = comp.bRepBodies.item(0)
    occ.activate()
    sk = sketch(comp, comp.yZConstructionPlane, 'pente')
    o = sk.modelToSketchSpace(P3(0, 0, 0))

    def sp_(y, z):
        p = sk.modelToSketchSpace(P3(0, y, z))
        return P3(p.x, p.y, 0)
    uy = sk.modelToSketchSpace(P3(0, 1, 0))
    y_is_x = abs(uy.x - o.x) > abs(uy.y - o.y)          # l'axe Y modèle est-il l'axe x de l'esquisse ?
    ORI_Y, ORI_Z = (HOR, VER) if y_is_x else (VER, HOR)

    def along(line, axis):
        g = sk.geometricConstraints
        if (axis == 'y') == y_is_x:
            g.addHorizontal(line)
        else:
            g.addVertical(line)

    y1, z1 = -ev('platine_ep + visiere_P'), ev('aff_z + visiere_dz_haut - visiere_ep')
    y2, z2 = -ev('platine_ep + visiere_P_bas'), ev('aff_z') - ev('visiere_dz_bas')
    y4, z3 = -ev('platine_ep + visiere_P + 2 mm'), z2 - 0.2
    L = sk.sketchCurves.sketchLines
    l12 = L.addByTwoPoints(sp_(y1, z1), sp_(y2, z2))
    l23 = L.addByTwoPoints(l12.endSketchPoint, sp_(y2, z3))
    l34 = L.addByTwoPoints(l23.endSketchPoint, sp_(y4, z3))
    l45 = L.addByTwoPoints(l34.endSketchPoint, sp_(y4, z1))
    l51 = L.addByTwoPoints(l45.endSketchPoint, l12.startSketchPoint)
    along(l23, 'z'); along(l34, 'y'); along(l45, 'z'); along(l51, 'y')
    D = sk.sketchDimensions
    p1, p2, p4 = l12.startSketchPoint, l12.endSketchPoint, l34.endSketchPoint
    D.addDistanceDimension(sk.originPoint, p1, ORI_Y, sp_(y1 / 2, z1 + 0.3)).parameter.expression = 'platine_ep + visiere_P'
    D.addDistanceDimension(sk.originPoint, p1, ORI_Z, sp_(y1 - 0.3, z1 / 2)).parameter.expression = \
        'aff_z + visiere_dz_haut - visiere_ep'
    D.addDistanceDimension(sk.originPoint, p2, ORI_Y, sp_(y2 / 2, z2 - 0.3)).parameter.expression = \
        'platine_ep + visiere_P_bas'
    D.addDistanceDimension(sk.originPoint, p2, ORI_Z, sp_(y2 + 0.3, z2 / 2)).parameter.expression = 'visiere_dz_bas - aff_z'
    D.addDistanceDimension(l23.startSketchPoint, l23.endSketchPoint, ORI_Z, sp_(y2 + 0.3, z2 - 0.1)).parameter.expression = '2 mm'
    D.addDistanceDimension(sk.originPoint, p4, ORI_Y, sp_(y4 / 2, z3 - 0.3)).parameter.expression = \
        'platine_ep + visiere_P + 2 mm'

    ext = comp.features.extrudeFeatures
    inp = ext.createInput(sk.profiles.item(0), CUT)
    inp.setSymmetricExtent(VI('visiere_L + 10 mm'), True)
    inp.participantBodies = [body]
    ext.add(inp).name = 'pente'
    d.activateRootComponent()
    bb = body.boundingBox
    print('visiere', bbox_mm(body), 'vol', round(body.volume * 1000, 1), 'mm3', 'profils', sk.profiles.count,
          'unhealthy', unhealthy())
    # saillie mesurée sur une joue : en bas et juste sous le toit
    for z in (z2 + 0.01, z1 - 0.01):
        r = comp.findBRepUsingRay(P3(ev('visiere_L') / 2 - ev('visiere_ep') / 2, -5, z), adsk.core.Vector3D.create(0, 1, 0),
                                  adsk.fusion.BRepEntityTypes.BRepFaceEntityType, -1.0, True, None)
        print('joue z=%.1f : face avant à y=%.2f' % (z * 10, min(f.pointOnFace.y for f in r) * 10 if r.count else 0))
