"""Plaque du cadran SO-45 d'origine, mesurée sur photo redressée.
Cotes de design/dials/dial_so45_spec.json (bloc plate), en mm.
Repère : plaque à plat sur XY, face visible vers +Z, x à droite, y = haut du cadran."""
import math
import adsk.core, adsk.fusion

R, DOME_Y, DOME_R = 20.4, -8.2, 8.76
SH_Y, FIL_R, SLOT_W = -5.22, 3.53, 12.31
HOLE_X, HOLE_Y, HOLE_D = 15.31, -2.3, 2.6
PIVOT_Y = -8.95
BASE_R = (18.54, 18.95)
A0, A5 = -39.11, 37.81          # traits 0 V et 5 V, angle depuis +y (positif à droite)
WIN_R, CHORD_Y = 19.4, -11.6    # fenêtre : modèle GrabCAD ; bord du masque : photo de face (±0,5)


def P(x, y):
    return adsk.core.Point3D.create(x / 10, y / 10, 0)


def run(ctx):
    app = adsk.core.Application.get()
    d = adsk.fusion.Design.cast(app.activeProduct)
    root = d.rootComponent
    if not d.userParameters.itemByName("ep_cadran"):
        d.userParameters.add("ep_cadran", adsk.core.ValueInput.createByString("0.5 mm"), "mm",
                             "épaisseur de la plaque d'origine (à mesurer)")

    # --- contour de la plaque
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = "plaque"
    arcs, lines = sk.sketchCurves.sketchArcs, sk.sketchCurves.sketchLines
    ty = -math.sqrt(R * R - SLOT_W * SLOT_W)                 # pointes
    dx = math.sqrt(DOME_R ** 2 - (SH_Y - DOME_Y) ** 2)       # pied du dôme
    a_tip = math.degrees(math.atan2(ty, SLOT_W))
    outer = arcs.addByCenterStartSweep(P(0, 0), P(SLOT_W, ty), math.radians(180 - 2 * a_tip))
    a_d = math.degrees(math.atan2(SH_Y - DOME_Y, dx))
    dome = arcs.addByCenterStartSweep(P(0, DOME_Y), P(dx, SH_Y), math.radians(180 - 2 * a_d))
    fr = arcs.addByCenterStartSweep(P(SLOT_W - FIL_R, SH_Y - FIL_R), P(SLOT_W, SH_Y - FIL_R), math.radians(90))
    fl = arcs.addByCenterStartSweep(P(-SLOT_W + FIL_R, SH_Y - FIL_R), P(-SLOT_W + FIL_R, SH_Y), math.radians(90))
    lines.addByTwoPoints(dome.startSketchPoint, fr.endSketchPoint)       # épaulement droit
    lines.addByTwoPoints(fl.startSketchPoint, dome.endSketchPoint)       # épaulement gauche
    lines.addByTwoPoints(outer.startSketchPoint, fr.startSketchPoint)    # flanc droit
    lines.addByTwoPoints(fl.endSketchPoint, outer.endSketchPoint)        # flanc gauche
    for sx in (-1, 1):
        sk.sketchCurves.sketchCircles.addByCenterRadius(P(sx * HOLE_X, HOLE_Y), HOLE_D / 20)
    prof = max(sk.profiles, key=lambda p: p.areaProperties().area)
    ext = root.features.extrudeFeatures.addSimple(prof, adsk.core.ValueInput.createByString("ep_cadran"),
                                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    body = ext.bodies.item(0)
    body.name = "plaque_origine"
    ext.name = "plaque"

    # --- repères : axe, échelle d'origine, débattement, fenêtre et masque (modèle GrabCAD)
    rk = root.sketches.add(root.xYConstructionPlane)
    rk.name = "reperes"
    rk.sketchPoints.add(P(0, PIVOT_Y))
    t0, t5 = 90 - A0, 90 - A5                                # angles trigo
    for r in BASE_R:
        rk.sketchCurves.sketchArcs.addByCenterStartSweep(
            P(0, PIVOT_Y), P(r * math.cos(math.radians(t5)), PIVOT_Y + r * math.sin(math.radians(t5))),
            math.radians(t0 - t5))
    for t in (t0, t5):
        ln = rk.sketchCurves.sketchLines.addByTwoPoints(
            P(0, PIVOT_Y), P(23 * math.cos(math.radians(t)), PIVOT_Y + 23 * math.sin(math.radians(t))))
        ln.isConstruction = True
    w = rk.sketchCurves.sketchCircles.addByCenterRadius(P(0, 0), WIN_R / 10)
    w.isConstruction = True
    cx = math.sqrt(WIN_R ** 2 - CHORD_Y ** 2)
    c = rk.sketchCurves.sketchLines.addByTwoPoints(P(-cx, CHORD_Y), P(cx, CHORD_Y))
    c.isConstruction = True

    bb = body.boundingBox
    print(f"corps {body.name} : {(bb.maxPoint.x - bb.minPoint.x) * 10:.2f} x {(bb.maxPoint.y - bb.minPoint.y) * 10:.2f} x "
          f"{(bb.maxPoint.z - bb.minPoint.z) * 10:.2f} mm, aire face {prof.areaProperties().area * 100:.1f} mm², "
          f"profils {sk.profiles.count}, faces {body.faces.count}")


def canvas(ctx):
    """Photo redressée en canevas sous la plaque (25 px/mm, 1350 px = 54 mm,
    centrée sur l'origine). L'image vient de la vue redressée,
    copiée dans le Temp Windows (cadran_redresse_25ppmm.jpg). Le canevas d'une
    image se cale par une matrice 2D : l'image entière = carré unité."""
    import os
    d = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    root = d.rootComponent
    img = os.path.join(os.environ["TEMP"], "claudemetre", "cadran_redresse_25ppmm.jpg")
    c = root.canvases.add(root.canvases.createInput(img, root.xYConstructionPlane))
    c.name = "photo_redressee"
    m = adsk.core.Matrix2D.create()
    m.setWithArray([5.4, 0, -2.7, 0, 5.4, -2.7, 0, 0, 1])
    c.transform = m
    root.bRepBodies.itemByName("plaque_origine").opacity = 0.4


def imprime(ctx):
    """Cadran imprimé : couche de face ep_face au-dessus de
    l'appui (z = 0, haut des piliers), renfort ep_dos dessous sauf les
    lamages Ø d_pilier + 2 jeu_pilier autour des trous ; piliers en repère.
    Mêmes cotes que so45_print.py (bloc print de dial_so45_spec.json)."""
    d = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    root = d.rootComponent
    VI = adsk.core.ValueInput.createByString
    for n, v, c in (("ep_face", "0.8 mm", "couche de face, en couleurs ; épaisseur à l'appui sur les piliers"),
                    ("ep_dos", "1.2 mm", "renfort du dos, couleur du fond"),
                    ("d_pilier", "5 mm", "piliers de fixation du cadran (Ø 4 d'après la photo, 5 mesuré)"),
                    ("jeu_pilier", "0.2 mm", "jeu radial des lamages")):
        if not d.userParameters.itemByName(n):
            d.userParameters.add(n, VI(v), "mm", c)
    ext = root.features.extrudeFeatures
    NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
    prof = max(root.sketches.itemByName("plaque").profiles, key=lambda p: p.areaProperties().area)

    face = ext.addSimple(prof, VI("ep_face"), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    face.name = "imprime_face"
    body = face.bodies.item(0)
    body.name = "cadran_imprime"
    inp = ext.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI("ep_dos")), NEG)
    inp.participantBodies = [body]
    ext.add(inp).name = "imprime_dos"

    def circles(name, expr):
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.name = name
        out = []
        for sx in (-1, 1):
            c = sk.sketchCurves.sketchCircles.addByCenterRadius(P(sx * HOLE_X, HOLE_Y), 0.22)
            c.centerSketchPoint.isFixed = True
            dim = sk.sketchDimensions.addDiameterDimension(c, P(sx * HOLE_X, HOLE_Y + 4))
            dim.parameter.expression = expr
            out.append(c)
        return sk

    lam = circles("lamages", "d_pilier + 2 * jeu_pilier")
    col = adsk.core.ObjectCollection.create()
    for p in lam.profiles:
        col.add(p)
    inp = ext.createInput(col, adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI("ep_dos")), NEG)
    inp.participantBodies = [body]
    ext.add(inp).name = "lamages"

    pil = circles("piliers", "d_pilier")
    col = adsk.core.ObjectCollection.create()
    for p in pil.profiles:
        col.add(p)
    inp = ext.createInput(col, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI("5 mm")), NEG)
    f = ext.add(inp)
    f.name = "piliers_repere"
    for k, b in enumerate(f.bodies):
        b.name = f"pilier_repere_{k + 1}"
        b.opacity = 0.5
    root.bRepBodies.itemByName("plaque_origine").isLightBulbOn = False
    lam.isVisible = pil.isVisible = False

    bb = body.boundingBox
    print(f"{body.name} : z {bb.minPoint.z * 10:.2f} .. {bb.maxPoint.z * 10:.2f} mm, volume {body.volume * 1000:.1f} mm³, "
          f"faces {body.faces.count}, corps {root.bRepBodies.count}")


def plaque_parametree(ctx):
    """Rayon du cadran et entraxe des trous en paramètres favoris : r_plaque 20,2 (la plaque mesurée sur photo,
    20,4, entre trop juste) et entraxe_trous 31,02 (30,62 sur photo, trop
    serré). Esquisse plaque : tout fixé sauf l'arc extérieur, dont les
    extrémités glissent sur les flancs verticaux ; trous, lamages et piliers
    cotés depuis l'origine."""
    VI = adsk.core.ValueInput.createByString
    H = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
    V = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
    d = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    root = d.rootComponent
    for n, v, c in (("r_plaque", "20.2 mm", "rayon du cadran imprimé (plaque d'origine : 20,4 sur photo)"),
                    ("entraxe_trous", "31.02 mm", "entraxe des trous de fixation (30,62 sur photo)")):
        p = d.userParameters.itemByName(n) or d.userParameters.add(n, VI(v), "mm", c)
        p.isFavorite = True

    def _try(f):
        """Fusion refuse comme redondante la seconde contrainte de deux points
        de même y (cote verticale, flanc vertical) : il les tient alignés."""
        try:
            return f()
        except RuntimeError as e:
            if "OVER_CONSTRAINTS" not in str(e):
                raise
            return None

    def place(sk, circle, diameter=None):
        """Centre du cercle coté depuis l'origine : x = ±entraxe/2, y = HOLE_Y."""
        c = circle.centerSketchPoint
        c.isFixed = False
        x, y = c.geometry.x, c.geometry.y
        dims = sk.sketchDimensions
        out = [(dims.addDistanceDimension(sk.originPoint, c, H, adsk.core.Point3D.create(x / 2, y - 0.3, 0)),
                "entraxe_trous / 2"),
               (_try(lambda: dims.addDistanceDimension(sk.originPoint, c, V, adsk.core.Point3D.create(x + 0.3, y / 2, 0))),
                f"{-HOLE_Y} mm")]
        if diameter:
            out.append((_try(lambda: dims.addDiameterDimension(circle, adsk.core.Point3D.create(x, y + 0.3, 0))), diameter))
        return out

    sk = root.sketches.itemByName("plaque")
    outer = max(sk.sketchCurves.sketchArcs, key=lambda a: a.radius)
    tips = [outer.startSketchPoint, outer.endSketchPoint]
    holes = list(sk.sketchCurves.sketchCircles)
    free = tips + [h.centerSketchPoint for h in holes]       # == et non entityToken : jeton instable
    for pt in sk.sketchPoints:
        if not pt.isFixed and not any(pt == q for q in free):
            pt.isFixed = True
    flank = [ln for ln in sk.sketchCurves.sketchLines
             if any(e == t for e in (ln.startSketchPoint, ln.endSketchPoint) for t in tips)][0]
    sk.geometricConstraints.addVertical(flank)          # l'autre flanc suit (voir _try)
    radius = sk.sketchDimensions.addRadialDimension(outer, adsk.core.Point3D.create(0, outer.radius + 0.3, 0))
    dims = [dim for h in holes for dim in place(sk, h, f"{HOLE_D} mm")]
    sketches = [sk] + [root.sketches.itemByName(n) for n in ("lamages", "piliers")]
    for s in sketches[1:]:
        dims += [dim for c in s.sketchCurves.sketchCircles for dim in place(s, c)]
    radius.parameter.expression = "r_plaque"
    for dim, expr in dims:
        if dim:
            dim.parameter.expression = expr
    xs = [round(t.geometry.x * 10, 3) for t in tips]
    assert all(abs(abs(x) - SLOT_W) < 1e-3 for x in xs), f"pointes hors des flancs : {xs}"
    half = d.userParameters.itemByName("entraxe_trous").value * 5           # cm -> mm, / 2
    centres = [(round(c.centerSketchPoint.geometry.x * 10, 3), round(c.centerSketchPoint.geometry.y * 10, 3),
                round(c.radius * 20, 2)) for s in sketches for c in s.sketchCurves.sketchCircles]
    assert all(abs(abs(x) - half) < 1e-3 and abs(y - HOLE_Y) < 1e-3 for x, y, _ in centres), centres
    tl = d.timeline
    print(f"rayon {outer.radius * 10:.3f} | pointes {xs} y {tips[0].geometry.y * 10:.3f} | cercles {centres} | "
          f"profils {sk.profiles.count} | erreurs {[tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != 0]}")


APP_LIB = "BA5EE55E-9982-449B-9D66-9F036540E140"   # Fusion Appearance Library


def _appearance(d, name, rgb):
    a = d.appearances.itemByName(name)
    if a:
        return a
    app = adsk.core.Application.get()
    a = d.appearances.addByCopy(app.materialLibraries.itemById(APP_LIB).appearances.itemById("Prism-127"), name)
    for i in range(a.appearanceProperties.count):
        p = a.appearanceProperties.item(i)
        if isinstance(p, adsk.core.ColorProperty) and p.id in ("opaque_albedo", "generic_diffuse"):
            p.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
    return a


def _match(sk, polys):
    """Profils à incruster : un par polygone (aire et centre en mm), pas les contre-formes."""
    found = []
    for q in polys:
        for p in sk.profiles:
            ap = p.areaProperties()
            if abs(ap.area * 100 - q["area"]) <= 0.02 * q["area"] + 0.01 and \
                    abs(ap.centroid.x * 10 - q["cx"]) < 0.05 and abs(ap.centroid.y * 10 - q["cy"]) < 0.05:
                found.append(p)
                break
    if len(found) != len(polys):
        raise RuntimeError(f"{sk.name} : {len(found)}/{len(polys)} profils reconnus sur {sk.profiles.count}")
    coll = adsk.core.ObjectCollection.create()
    for p in found:
        coll.add(p)
    return coll


def _index():
    import os, json
    src = os.path.join(os.environ["TEMP"], "claudemetre", "cadran_dxf")
    return src, json.load(open(os.path.join(src, "cadran.json"), encoding="utf-8"))


def derive(ctx):
    """Variante d'un cadran : nouveau design, non enregistré,
    dérivé de fond-jauge (le modèle, enregistré) : composant fond et paramètres
    favoris, qui arrivent suffixés _Ref (ep_face_Ref, prof_couleur_Ref…).
    Ensuite variante(). À enregistrer sous fond-jauge-<session|semaine>."""
    app = adsk.core.Application.get()
    src_doc = [doc for doc in app.documents if doc.name == "fond-jauge"][0]
    src = adsk.fusion.Design.cast(src_doc.products.itemByProductType("DesignProductType"))
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    d.designIntent = 2                                  # Hybrid : un design Part n'a qu'un composant
    d.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    dfs = d.rootComponent.features.deriveFeatures
    inp = dfs.createInput(src)
    inp.sourceEntities = [src.rootComponent.occurrences.itemByName("fond:1")]
    inp.isIncludeFavoriteParameters = True
    dfs.add(inp)


def variante(ctx):
    """Couleurs d'un cadran dans un design dérivé (derive()), d'après
    cadran_dxf/ (uv run cadran_dxf.py <style> <session|semaine>, copié dans
    %TEMP%/claudemetre/cadran_dxf/). Dans le composant fond : plan_face
    (ep_face_Ref), esquisses cadran_<couleur>, logements incruste_<couleur>
    découpés dans le corps dérivé sur prof_couleur_Ref. Un composant par
    filament (echelle, zone, texte) : à l'export 3MF, chaque composant donne un
    objet. Fusion ne réunit pas des corps disjoints (Combine les laisse
    séparés, sans erreur) : un corps par morceau. Relancé, remplace les
    couleurs précédentes (nouveau DXF après un changement du générateur)."""
    import os
    app = adsk.core.Application.get()
    d = adsk.fusion.Design.cast(app.activeProduct)
    assert app.activeDocument.name != "fond-jauge", "à lancer dans une variante, pas dans le modèle"
    root = d.rootComponent
    VI = adsk.core.ValueInput.createByString
    NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection
    src, index = _index()
    doc_name = app.activeDocument.name                  # DXF de l'autre cadran encore dans le Temp
    assert not doc_name.startswith("fond-jauge-") or doc_name.endswith(index["dial"]), \
        f"{doc_name} : DXF du cadran {index['dial']}"
    fc = root.occurrences.itemByName("fond:1").component
    fond = fc.bRepBodies.item(0)
    fond.name = "fond"
    fond.appearance = _appearance(d, "PLA fond", index["rgb"]["fond"])

    for name in index["bodies"]:                        # couleurs précédentes
        occ = root.occurrences.itemByName(name + ":1")
        if occ:
            occ.deleteMe()
        for coll, prefix in ((fc.features.extrudeFeatures, "incruste_"), (fc.sketches, "cadran_")):
            old = coll.itemByName(prefix + name)
            if old:
                old.deleteMe()
    if fc.constructionPlanes.itemByName("plan_face"):
        fc.constructionPlanes.itemByName("plan_face").deleteMe()

    def face_plane(comp):
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(comp.xYConstructionPlane, VI("ep_face_Ref"))
        pl = comp.constructionPlanes.add(pi)
        pl.name = "plan_face"
        pl.isLightBulbOn = False
        return pl

    def dxf(comp, plane, name, polys):
        opt = app.importManager.createDXF2DImportOptions(os.path.join(src, name + ".dxf"), plane)
        opt.isSingleSketchResult = True
        sk = [r for r in app.importManager.importToTarget2(opt, comp) if isinstance(r, adsk.fusion.Sketch)][0]
        sk.name = "cadran_" + name
        sk.isVisible = False
        return _match(sk, polys)

    log = [f"cadran {index['dial']} ({index['style']})"]
    plane = face_plane(fc)
    for name, polys in index["bodies"].items():
        inp = fc.features.extrudeFeatures.createInput(dxf(fc, plane, name, polys),
                                                      adsk.fusion.FeatureOperations.CutFeatureOperation)
        inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI("prof_couleur_Ref")), NEG)
        inp.participantBodies = [fond]
        fc.features.extrudeFeatures.add(inp).name = "incruste_" + name

        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = name
        inp = comp.features.extrudeFeatures.createInput(dxf(comp, face_plane(comp), name, polys),
                                                        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI("prof_couleur_Ref")), NEG)
        f = comp.features.extrudeFeatures.add(inp)
        f.name = name
        look = _appearance(d, "PLA " + name, index["rgb"][name])
        for k in range(f.bodies.count):
            b = f.bodies.item(k)
            b.name = f"{name}_{k + 1}"
            b.appearance = look
        occ.isLightBulbOn = True
        log.append(f"{name} : {f.bodies.count} corps, {sum(b.volume for b in f.bodies) * 1000:.1f} mm³")
    tl = d.timeline
    bad = [(tl.item(i).name, tl.item(i).errorOrWarningMessage) for i in range(tl.count) if tl.item(i).healthState != 0]
    log.append(f"fond : {fond.volume * 1000:.1f} mm³ | erreurs : {bad}")
    print("\n".join(log))
