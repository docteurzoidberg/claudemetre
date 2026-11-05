# Outils communs aux scripts Fusion du Claudemètre (exécutés dans Fusion).
# Repère : origine au centre de la façade de la coque, X à droite, Z en haut,
# +Y vers le mur. Unités API = cm ; les expressions sont en mm.
import adsk.core, adsk.fusion

app = adsk.core.Application.get()
VI = adsk.core.ValueInput.createByString
P3 = adsk.core.Point3D.create
HOR = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
VER = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection


def design():
    return adsk.fusion.Design.cast(app.activeProduct)


def ev(expr):
    """Valeur d'une expression en unités internes (cm)."""
    return design().unitsManager.evaluateExpression(expr, 'mm')


def set_params(rows):
    up = design().userParameters
    for name, expr, comment in rows:
        p = up.itemByName(name)
        if p:
            p.expression = expr
            p.comment = comment
        else:
            up.add(name, VI(expr), 'mm', comment)


def y_sign(comp):
    """+1 si la normale du plan XZ du composant est +Y."""
    return 1 if comp.xZConstructionPlane.geometry.normal.y > 0 else -1


def toward_wall(comp):
    """Sens d'extrusion vers +Y (le mur) pour une esquisse parallèle à XZ."""
    return POS if y_sign(comp) > 0 else NEG


def toward_front(comp):
    return NEG if y_sign(comp) > 0 else POS


def plane_y(comp, expr, name):
    """Plan parallèle à XZ, à y = expr (mm, vers le mur)."""
    cpi = comp.constructionPlanes.createInput()
    e = expr if y_sign(comp) > 0 else '-(' + expr + ')'
    cpi.setByOffset(comp.xZConstructionPlane, VI(e))
    pl = comp.constructionPlanes.add(cpi)
    pl.name = name
    return pl


def sketch(comp, plane, name):
    sk = comp.sketches.add(plane)
    sk.name = name
    return sk


def spt(sk, x, z):
    """Point d'esquisse pour la position modèle (x, z), en cm."""
    p = sk.modelToSketchSpace(P3(x, 0, z))
    return P3(p.x, p.y, 0)


def pair_points(sk, xr, xl, z, xr_e, xl_e, z_e):
    """Deux points à la même hauteur z, cotés depuis l'origine (distances positives ;
    xr, xl, z en cm, avec leur signe, pour poser la géométrie)."""
    P = sk.sketchPoints
    r = P.add(spt(sk, xr, z))
    l = P.add(spt(sk, xl, z))
    d, g = sk.sketchDimensions, sk.geometricConstraints
    d.addDistanceDimension(sk.originPoint, r, HOR, spt(sk, xr / 2, z + 0.3)).parameter.expression = xr_e
    d.addDistanceDimension(sk.originPoint, r, VER, spt(sk, xr + 0.3, z / 2)).parameter.expression = z_e
    d.addDistanceDimension(sk.originPoint, l, HOR, spt(sk, xl / 2, z - 0.3)).parameter.expression = xl_e
    g.addHorizontalPoints(r, l)
    return [r, l]


def point(sk, cx_e, cz_e, sx=1, sz=1):
    """Point de construction coté depuis l'origine (expressions positives,
    sx / sz = côté)."""
    x, z = sx * ev(cx_e), sz * ev(cz_e)
    p = sk.sketchPoints.add(spt(sk, x, z))
    d = sk.sketchDimensions
    d.addDistanceDimension(sk.originPoint, p, HOR, spt(sk, x / 2, z + 0.3)).parameter.expression = cx_e
    d.addDistanceDimension(sk.originPoint, p, VER, spt(sk, x + 0.3, z / 2)).parameter.expression = cz_e
    return p, x, z


def rect(sk, w_e, h_e, x0_e, z0_e, sx=-1, sz=-1, cx=0.0, cz=0.0):
    """Rectangle w x h ; son coin (sx, sz) (-1 = côté négatif) est coté depuis
    l'origine par x0_e / z0_e (distances positives). cx, cz : centre (cm),
    seulement pour poser la géométrie au bon endroit avant les cotes."""
    w, h = ev(w_e), ev(h_e)
    pts = [spt(sk, cx - w / 2, cz - h / 2), spt(sk, cx + w / 2, cz - h / 2),
           spt(sk, cx + w / 2, cz + h / 2), spt(sk, cx - w / 2, cz + h / 2)]
    L = sk.sketchCurves.sketchLines
    l0 = L.addByTwoPoints(pts[0], pts[1])
    l1 = L.addByTwoPoints(l0.endSketchPoint, pts[2])
    l2 = L.addByTwoPoints(l1.endSketchPoint, pts[3])
    l3 = L.addByTwoPoints(l2.endSketchPoint, l0.startSketchPoint)
    g = sk.geometricConstraints
    g.addHorizontal(l0); g.addHorizontal(l2); g.addVertical(l1); g.addVertical(l3)
    d = sk.sketchDimensions
    d.addDistanceDimension(l0.startSketchPoint, l0.endSketchPoint, HOR,
                           spt(sk, cx, cz - h / 2 - 0.5)).parameter.expression = w_e
    d.addDistanceDimension(l1.startSketchPoint, l1.endSketchPoint, VER,
                           spt(sk, cx + w / 2 + 0.5, cz)).parameter.expression = h_e
    corner = {(-1, -1): l0.startSketchPoint, (1, -1): l1.startSketchPoint,
              (1, 1): l2.startSketchPoint, (-1, 1): l3.startSketchPoint}[(sx, sz)]
    px, pz = cx + sx * w / 2, cz + sz * h / 2
    d.addDistanceDimension(sk.originPoint, corner, HOR, spt(sk, px / 2, pz + 0.4)).parameter.expression = x0_e
    d.addDistanceDimension(sk.originPoint, corner, VER, spt(sk, px + 0.4, pz / 2)).parameter.expression = z0_e
    return [l0, l1, l2, l3]


def centered_rect(sk, w_e, h_e):
    return rect(sk, w_e, h_e, '(%s) / 2' % w_e, '(%s) / 2' % h_e)


def four_points(sk, ctr, cx, cz, dx_e, dz_e):
    """4 points en (cx ± dx, cz ± dz) autour du point ctr (même logique de cotes)."""
    dx, dz = ev(dx_e), ev(dz_e)
    P = sk.sketchPoints
    tr = P.add(spt(sk, cx + dx, cz + dz))
    tl = P.add(spt(sk, cx - dx, cz + dz))
    br = P.add(spt(sk, cx + dx, cz - dz))
    bl = P.add(spt(sk, cx - dx, cz - dz))
    d, g = sk.sketchDimensions, sk.geometricConstraints
    d.addDistanceDimension(ctr, tr, HOR, spt(sk, cx + dx / 2, cz + dz + 0.3)).parameter.expression = dx_e
    d.addDistanceDimension(ctr, tr, VER, spt(sk, cx + dx + 0.3, cz + dz / 2)).parameter.expression = dz_e
    d.addDistanceDimension(ctr, tl, HOR, spt(sk, cx - dx / 2, cz + dz + 0.3)).parameter.expression = dx_e
    g.addHorizontalPoints(tr, tl)
    d.addDistanceDimension(ctr, br, VER, spt(sk, cx + dx + 0.3, cz - dz / 2)).parameter.expression = dz_e
    g.addVerticalPoints(tr, br)
    g.addHorizontalPoints(br, bl)
    g.addVerticalPoints(tl, bl)
    return [tr, tl, br, bl]


def two_points(sk, ctr, cx, cz, dx_e):
    """2 points en (cx ± dx, cz), à la hauteur du point ctr."""
    dx = ev(dx_e)
    P = sk.sketchPoints
    r = P.add(spt(sk, cx + dx, cz))
    l = P.add(spt(sk, cx - dx, cz))
    d, g = sk.sketchDimensions, sk.geometricConstraints
    d.addDistanceDimension(ctr, r, HOR, spt(sk, cx + dx / 2, cz + 0.3)).parameter.expression = dx_e
    d.addDistanceDimension(ctr, l, HOR, spt(sk, cx - dx / 2, cz + 0.3)).parameter.expression = dx_e
    g.addHorizontalPoints(ctr, r)
    g.addHorizontalPoints(ctr, l)
    return [r, l]


def circles_at(sk, pts, d_e):
    """Cercles de diamètre d_e centrés sur des points existants (égaux au premier)."""
    C = sk.sketchCurves.sketchCircles
    r = ev(d_e) / 2
    out = []
    for p in pts:
        c = C.addByCenterRadius(p, r)
        out.append(c)
    g = sk.geometricConstraints
    q = out[0].centerSketchPoint.geometry
    sk.sketchDimensions.addDiameterDimension(out[0], P3(q.x + r + 0.3, q.y + r + 0.3, 0)).parameter.expression = d_e
    for c in out[1:]:
        g.addEqual(out[0], c)
    return out


def hole(comp, pts, kind, d_e, depth_e, wall_side, name, bodies=None, cb_d=None, cb_p=None, csk_d=None):
    """Perçage à fond plat depuis des points d'esquisse (plan parallèle à XZ).
    kind : 'simple', 'lamage' (logement d'insert), 'fraise' (tête fraisée 90°).
    wall_side : True = le perçage va vers le mur (+Y), False = vers l'avant."""
    hf = comp.features.holeFeatures
    if kind == 'lamage':
        hi = hf.createCounterboreInput(VI(d_e), VI(cb_d), VI(cb_p))
    elif kind == 'fraise':
        hi = hf.createCountersinkInput(VI(d_e), VI(csk_d), VI('90 deg'))
    else:
        hi = hf.createSimpleInput(VI(d_e))
    coll = adsk.core.ObjectCollection.create()
    for p in pts:
        coll.add(p)
    hi.setPositionBySketchPoints(coll)
    hi.setDistanceExtent(VI(depth_e))
    # Par défaut, le perçage part à l'opposé de la normale de l'esquisse.
    sk = pts[0].parentSketch
    ny = sk.xDirection.crossProduct(sk.yDirection).y
    hi.isDefaultDirection = (ny < 0) == wall_side
    if bodies is not None:
        hi.participantBodies = bodies
    h = hf.add(hi)
    h.name = name
    h.tipAngle.expression = '180 deg'
    return h


def profiles(sk):
    return [sk.profiles.item(i) for i in range(sk.profiles.count)]


def prof_area(p):
    return p.areaProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy).area


def extrude(comp, prof, op, dist_e, direction, name, bodies=None):
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(prof, op)
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI(dist_e)), direction)
    if bodies is not None:
        inp.participantBodies = bodies
    f = ext.add(inp)
    f.name = name
    return f


def fillet(comp, edges, r_e, name):
    coll = adsk.core.ObjectCollection.create()
    for e in edges:
        coll.add(e)
    ff = comp.features.filletFeatures
    inp = ff.createInput()
    inp.edgeSetInputs.addConstantRadiusEdgeSet(coll, VI(r_e), True)
    f = ff.add(inp)
    f.name = name
    return f


def mirror(comp, feats, plane, name):
    coll = adsk.core.ObjectCollection.create()
    for f in feats:
        coll.add(f)
    mf = comp.features.mirrorFeatures
    f = mf.add(mf.createInput(coll, plane))
    f.name = name
    return f


def bbox_mm(body):
    b = body.boundingBox
    return [round(v * 10, 2) for v in b.minPoint.asArray()], [round(v * 10, 2) for v in b.maxPoint.asArray()]


def new_component(name):
    root = design().rootComponent
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ


def unhealthy():
    tl = design().timeline
    out = []
    for i in range(tl.count):
        it = tl.item(i)
        if it.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            out.append((it.name, it.errorOrWarningMessage))
    return out
