# Segments de l'afficheur : vert du STEP -> jaune du vrai module. Nouvelle version de afficheur_TM1637_056.
import adsk.core, adsk.fusion

FID = 'urn:adsk.wipprod:dm.lineage:l3rPYkDxRfWAsndd_VzZfA'
LIB = 'BA5EE55E-9982-449B-9D66-9F036540E140'


def appearance(d, name, src_id, rgb):
    a = d.appearances.itemByName(name)
    if a:
        return a
    src = adsk.core.Application.get().materialLibraries.itemById(LIB).appearances.itemById(src_id)
    a = d.appearances.addByCopy(src, name)
    for i in range(a.appearanceProperties.count):
        p = a.appearanceProperties.item(i)
        if isinstance(p, adsk.core.ColorProperty) and p.id in ('opaque_albedo', 'generic_diffuse'):
            p.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
    return a


def run(ctx):
    app = adsk.core.Application.get()
    home = app.activeDocument
    df = app.data.findFileById(FID)
    v0 = df.latestVersionNumber
    doc = app.documents.open(df, True)
    d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    a = appearance(d, 'Segments jaunes', 'Prism-129', (255, 186, 24))
    n = 0
    for b in d.rootComponent.bRepBodies:
        for f in b.faces:
            if f.appearance and f.appearance.name == 'Opaque(0,255,0)':
                f.appearance = a
                n += 1
    ok = doc.save('Segments jaunes (le module en stock est jaune)')
    print('faces', n, 'save', ok, 'version avant', v0)
    doc.close(False)
    home.activate()
