# Connecteur coudé retiré du modèle (4 broches + support) : le vrai module aura
# un connecteur droit vers l'arrière. Nouvelle version (v3) de
# afficheur_TM1637_056 ; les pastilles et la sérigraphie restent.
#
# À lancer avec `claudometre` fermé : quand le modèle est déjà chargé comme
# référence, documents.open() en donne une copie vide, et la fermer vide aussi
# l'exemplaire chargé. Ensuite, dans l'assemblage
# rouvert : DocumentReference.getLatestVersion() (215 -> 210 corps).
#
# Trois étapes (ouverture, suppression, enregistrement). Les corps du STEP sont dans une BaseFeature :
# deleteMe() hors édition invalide les autres objets corps.
import adsk.core, adsk.fusion

FID = 'urn:adsk.wipprod:dm.lineage:l3rPYkDxRfWAsndd_VzZfA'
BODIES = ['Body177', 'Body178', 'Body179', 'Body180', 'Body181']


def run(ctx):
    app = adsk.core.Application.get()
    df = app.data.findFileById(FID)
    v0 = df.latestVersionNumber
    doc = app.documents.open(df, True)
    d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    root = d.rootComponent
    n0 = root.bRepBodies.count
    if n0 != 215:
        doc.close(False)
        print('modèle inattendu (%d corps), fermé sans enregistrer' % n0)
        return
    bf = d.timeline.item(0).entity
    bf.startEdit()
    for name in BODIES:
        b = [b for b in bf.bodies if b.name == name][0]
        # Garde-fou : tout le connecteur est au bord droit du circuit (x > 27 mm).
        assert b.boundingBox.minPoint.x * 10 > 27, (name, b.boundingBox.minPoint.x * 10)
        b.deleteMe()
    bf.finishEdit()
    ok = doc.save('Connecteur coudé retiré (connecteur droit ou fils soudés sur le vrai module)')
    print('corps', n0, '->', root.bRepBodies.count, 'save', ok, 'version avant', v0)
    # L'envoi prend jusqu'à une minute : vérifier df.latestVersionNumber avant de fermer.
