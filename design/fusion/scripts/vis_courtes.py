# Crée vis_CHC_M3x12 et vis_CHC_M3x6 dans claudometre/models à partir de vis_CHC_M3x16
# (crazy 403/models) : copie, renommage, recoupe de la tige, enregistrement.
import adsk.core, adsk.fusion

SRC = 'urn:adsk.wipprod:dm.lineage:Xrudk5GKSmu7cjirih1WtA'
DST = 'urn:adsk.wipprod:fs.folder:co.IDhBrubqTFGBFUE9tCenHw'


def fix(ctx, fid, L):
    """Recoupe et enregistre une variante déjà copiée dont la version recoupée n'a pas été créée."""
    app = adsk.core.Application.get()
    home = app.activeDocument
    df = app.data.findFileById(fid)
    v0 = df.latestVersionNumber
    doc = app.documents.open(df, True)
    d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    r = d.rootComponent
    b = r.bRepBodies.item(0)
    zmin = round(b.boundingBox.minPoint.z * 10, 2)
    if abs(zmin + L) > 0.01:
        cpi = r.constructionPlanes.createInput()
        cpi.setByOffset(r.xYConstructionPlane, adsk.core.ValueInput.createByString('-%d mm' % L))
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
        ext.add(inp).name = 'longueur_%d' % L
    b.name = df.name
    z2 = round(b.boundingBox.minPoint.z * 10, 2)
    ok = doc.save('Variante M3x%d de vis_CHC_M3x16 (tige recoupée)' % L)
    print(df.name, 'v avant', v0, 'zmin avant', zmin, 'apres', z2, 'save', ok)
    doc.close(False)
    home.activate()


def run(ctx):
    app = adsk.core.Application.get()
    home = app.activeDocument
    dst = app.data.findFolderById(DST)
    have = {dst.dataFiles.item(i).name for i in range(dst.dataFiles.count)}
    for L in (12, 6):
        name = 'vis_CHC_M3x%d' % L
        if name in have:
            print('deja', name)
            continue
        df = app.data.findFileById(SRC).copy(dst)
        df.name = name
        doc = app.documents.open(df, True)
        d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        r = d.rootComponent
        b = r.bRepBodies.item(0)
        b.name = name
        cpi = r.constructionPlanes.createInput()
        cpi.setByOffset(r.xYConstructionPlane, adsk.core.ValueInput.createByString('-%d mm' % L))
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
        f = ext.add(inp)
        f.name = 'longueur_%d' % L
        bb = b.boundingBox
        zmin = round(bb.minPoint.z * 10, 2)
        if abs(zmin + L) > 0.01:
            raise RuntimeError('%s : bout de tige à %s au lieu de -%d (sens de coupe ?)' % (name, zmin, L))
        ok = doc.save('Variante M3x%d de vis_CHC_M3x16 (tige recoupée)' % L)
        print(name, 'zmin', zmin, 'zmax', round(bb.maxPoint.z * 10, 2), 'save', ok, df.id)
        doc.close(False)
    home.activate()
