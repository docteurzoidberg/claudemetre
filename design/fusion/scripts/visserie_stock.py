# Visserie adaptée au stock, après plaque_saillie.py : plus de FHC M3x8 ni M3x10.
# pilier() : perçages des inserts de platine approfondis pour une FHC M3x12 (pointe à y = 9).
# plaques() : plaques de flanc en CHC M3x6 à moitié noyées (lamage Ø 6 x 2) au lieu des FHC.
# modele_fhc12() : vis_FHC_M3x12 dans claudometre/models, recoupée de vis_FHC_M3x16 ; à lancer seul,
# il enregistre ce modèle (pas le design principal). remplace_fhc() : FHC restantes passées en M3x12.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

CHC6 = 'urn:adsk.wipprod:dm.lineage:aAxEYmdfS_mcqoZ7HgwAAg'
FHC16 = 'urn:adsk.wipprod:dm.lineage:rwf5tLDSTKqcrDLKtVMPdg'
MODELS = 'urn:adsk.wipprod:fs.folder:co.IDhBrubqTFGBFUE9tCenHw'


def garde():
    assert app.activeDocument.name.startswith('claudometre'), app.activeDocument.name


def pilier(ctx):
    garde()
    set_params([('vis_coque_p', '10 mm', 'Coque : profondeur du perçage des inserts de platine (vis FHC M3x12, pointe à 9)')])
    print('vis_coque_p', round(ev('vis_coque_p') * 10, 2), 'alertes', unhealthy())


def plaques(ctx):
    garde()
    d = design()
    root = d.rootComponent
    vocc = [o for o in root.occurrences if o.component.name == 'visserie'][0]
    occ = [o for o in root.occurrences if o.component.name == 'plaque_flanc'][0]
    comp = occ.component

    # 1. Retirer les vis et leurs liaisons : elles tiennent aux arêtes des fraisures.
    joints = [j for j in root.joints if j.name.startswith('vis_flanc_')]
    assert len(joints) == 8, len(joints)
    noms = {j.occurrenceOne.name for j in joints}
    assert len(noms) == 8, noms
    for j in joints:
        j.deleteMe()
    n = 0
    for o in list(vocc.component.occurrences):
        if o.name in noms:
            o.deleteMe()
            n += 1
    assert n == 8, n

    # 2. Fraisures remplacées par des lamages.
    set_params([('plaque_lamage_d', '6 mm', 'Plaque de flanc : diamètre du lamage des têtes CHC M3'),
                ('plaque_lamage_p', '2 mm', 'Plaque de flanc : profondeur du lamage, tête à moitié noyée')])
    hf = comp.features.holeFeatures
    hf.itemByName('plaque_vis').deleteMe()
    occ.activate()
    sk = comp.sketches.itemByName('vis')
    pts = [p for p in sk.sketchPoints if abs(p.geometry.x) > 0.1 and abs(p.geometry.y) > 0.1]
    assert len(pts) == 4, len(pts)
    body = comp.bRepBodies.item(0)
    hi = hf.createCounterboreInput(VI('vis_d'), VI('plaque_lamage_d'), VI('plaque_lamage_p'))
    coll = adsk.core.ObjectCollection.create()
    for p in pts:
        coll.add(p)
    hi.setPositionBySketchPoints(coll)
    hi.setDistanceExtent(VI('plaque_ep + plaque_saillie'))
    hi.isDefaultDirection = sk.xDirection.crossProduct(sk.yDirection).z > 0
    hi.participantBodies = [body]
    hv = hf.add(hi)
    hv.name = 'plaque_vis'
    hv.tipAngle.expression = '180 deg'
    d.activateRootComponent()

    # 3. CHC M3x6 liées au fond des lamages.
    xs = ev('coque_L / 2 + plaque_saillie - plaque_lamage_p')
    r = ev('plaque_lamage_d') / 2
    edges = []
    for o in [o for o in root.occurrences if o.component.name == 'plaque_flanc']:
        for e in o.bRepBodies.item(0).edges:
            g = e.geometry
            if isinstance(g, adsk.core.Circle3D) and abs(g.radius - r) < 1e-4 and abs(abs(g.center.x) - xs) < 1e-4:
                edges.append(e)
    assert len(edges) == 8, len(edges)
    noir = d.appearances.itemByName('Oxyde noir')
    df = app.data.findFileById(CHC6)
    flips = 0
    for i, e in enumerate(edges):
        sub = vocc.component.occurrences.addByInsert(df, adsk.core.Matrix3D.create(), True)
        sub.isGroundToParent = False
        o = sub.createForAssemblyContext(vocc)
        o.appearance = noir
        out = 1 if e.geometry.center.x > 0 else -1

        def joint(flip):
            g1 = adsk.fusion.JointGeometry.createByPoint(
                sub.component.originConstructionPoint.createForAssemblyContext(o))
            g2 = adsk.fusion.JointGeometry.createByCurve(e, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
            ji = root.joints.createInput(g1, g2)
            ji.setAsRigidJointMotion()
            ji.isFlipped = flip
            j = root.joints.add(ji)
            j.name = 'vis_flanc_%d' % (i + 1)
            return j

        j = joint(False)
        p, x, y, z = o.transform2.getAsCoordinateSystem()
        if z.x * out < 0:                     # la tête, vers +Z du modèle, doit sortir de la plaque
            j.deleteMe()
            j = joint(True)
            flips += 1
            p, x, y, z = o.transform2.getAsCoordinateSystem()
        if p.distanceTo(e.geometry.center) > 1e-4 or z.x * out < 0.999:
            raise RuntimeError('vis %d mal placée : %s %s' % (i + 1, p.asArray(), z.asArray()))
    print('CHC posées', len(edges), 'retournées', flips, 'visserie', vocc.component.occurrences.count,
          'alertes', unhealthy())


def modele_fhc12(ctx):
    home = app.activeDocument
    dst = app.data.findFolderById(MODELS)
    have = {dst.dataFiles.item(i).name for i in range(dst.dataFiles.count)}
    assert 'vis_FHC_M3x12' not in have, 'existe déjà'
    src = app.data.findFileById(FHC16)
    df = src.copy(dst)
    df.name = 'vis_FHC_M3x12'
    doc = app.documents.open(df, True)
    d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    r = d.rootComponent
    assert r.bRepBodies.count >= 1, ('corps', r.bRepBodies.count, r.allOccurrences.count)
    b = r.bRepBodies.item(0)
    b.name = 'vis_FHC_M3x12'
    cpi = r.constructionPlanes.createInput()
    cpi.setByOffset(r.xYConstructionPlane, adsk.core.ValueInput.createByString('-12 mm'))
    pl = r.constructionPlanes.add(cpi)
    pl.name = 'coupe_longueur'
    sk = r.sketches.add(pl)
    sk.name = 'coupe_longueur'
    sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(-1, -1, 0),
                                                     adsk.core.Point3D.create(1, 1, 0))
    ext = r.features.extrudeFeatures
    inp = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByString('10 mm')), adsk.fusion.ExtentDirections.NegativeExtentDirection)
    inp.participantBodies = [b]
    ext.add(inp).name = 'longueur_12'
    bb = b.boundingBox
    zmin, zmax = round(bb.minPoint.z * 10, 2), round(bb.maxPoint.z * 10, 2)
    if abs(zmin + 12) > 0.01:
        raise RuntimeError('bout de tige à %s au lieu de -12' % zmin)
    ok = doc.save('Variante M3x12 de vis_FHC_M3x16 (tige recoupée)')
    print('vis_FHC_M3x12 z', zmin, zmax, 'tete', round((bb.maxPoint.x - bb.minPoint.x) * 10, 2), 'save', ok, df.id)
    doc.close(False)
    home.activate()


def remplace_fhc(ctx, fid):
    garde()
    d = design()
    root = d.rootComponent
    vocc = [o for o in root.occurrences if o.component.name == 'visserie'][0]
    fhc = [o for o in vocc.component.occurrences if o.component.name.startswith('vis_FHC_M3x8')]
    assert len(fhc) == 10, len(fhc)
    ok = fhc[0].replace(app.data.findFileById(fid), True)
    noms = {}
    for o in vocc.component.occurrences:
        noms[o.component.name] = noms.get(o.component.name, 0) + 1
    print('replace', ok, noms, 'alertes', unhealthy())
