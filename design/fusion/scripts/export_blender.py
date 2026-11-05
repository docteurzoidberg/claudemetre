"""Export de l'assemblage `claudometre` pour la maquette Blender, relançable, sans rien modifier.

Maillage de chaque corps visible depuis l'extérieur, en mm dans le repère de la façade (origine au
centre de la façade, X à droite, Z en haut, +Y vers le mur), avec les normales de Fusion. Écrit
claudometre.bin (positions et normales float32, indices uint32, corps à la suite) et claudometre.json
(index : occurrence, corps, apparence, couleur, décalages, et pose de chaque occurrence) dans %TEMP%/claudemetre/export/blender/.
Recopier ensuite ces deux fichiers dans design/fusion/blender/ (`design/blender/variants6.py` les lit).

Laissés de côté, invisibles boîtier fermé : la carte, les clips, les inserts, et de l'afficheur tout
ce qui est derrière la face (circuit, broches). Corps masqués et occurrences éteintes ignorés. La face
de l'afficheur sort face par face : un corps par segment, pour pouvoir les allumer un à un.

`complet(ctx)` écrit la même chose avec tout l'intérieur, en moins fin, dans .../export/web/, pour la page
éclatée (`maquette/pack.py`), et avec toutes les plaques de flanc, même masquées, puisque la page les propose."""
import array
import json
import os
import adsk.core, adsk.fusion

SKIP = ('mrd076a_esp32_s3', 'clip_aile', 'clip_milieu', 'patron', 'visserie:1+insert', 'plaque_bossage:1+insert',
        'plaque_bossage_fusible:1+insert')
PLAQUES = ('plaque_flanc:1', 'plaque_bossage:1', 'plaque_bossage_fusible:1')
COLOR_IDS = ('opaque_albedo', 'generic_diffuse', 'metal_f0', 'layered_diffuse')


def couleur(a):
    if a is None:
        return None
    for i in range(a.appearanceProperties.count):
        p = a.appearanceProperties.item(i)
        if isinstance(p, adsk.core.ColorProperty) and p.id in COLOR_IDS and p.value:
            return [p.value.red, p.value.green, p.value.blue]
    return None


Q = adsk.fusion.TriangleMeshQualityOptions


def calcule(entity, qualite=Q.VeryHighQualityTriangleMesh):
    mc = entity.meshManager.createMeshCalculator()
    if isinstance(qualite, float):
        mc.surfaceTolerance = qualite  # flèche en cm : la qualité, elle, suit la taille du corps
    else:
        mc.setQuality(qualite)
    mc.maxNormalDeviation = 0  # sinon ×40 triangles, et la valeur reste d'un calculateur à l'autre
    return mc.calculate()


class Sortie:
    def __init__(self):
        self.pos = array.array('f')
        self.nor = array.array('f')
        self.idx = array.array('I')
        self.items = []

    def ajoute(self, meshes, m, info):
        """Applique la matrice m (4×4, cm) et range le tout en mm ; meshes : liste de TriangleMesh."""
        v0 = len(self.pos) // 3
        i0 = len(self.idx)
        lo = [1e9] * 3
        hi = [-1e9] * 3
        base = v0
        for mesh in meshes:
            c = mesh.nodeCoordinatesAsFloat
            n = mesh.normalVectorsAsFloat
            for k in range(0, len(c), 3):
                x, y, z = c[k], c[k + 1], c[k + 2]
                w = ((m[0] * x + m[1] * y + m[2] * z + m[3]) * 10,
                     (m[4] * x + m[5] * y + m[6] * z + m[7]) * 10,
                     (m[8] * x + m[9] * y + m[10] * z + m[11]) * 10)
                self.pos.extend(w)
                for a in range(3):
                    lo[a] = min(lo[a], w[a])
                    hi[a] = max(hi[a], w[a])
                x, y, z = n[k], n[k + 1], n[k + 2]
                self.nor.extend((m[0] * x + m[1] * y + m[2] * z, m[4] * x + m[5] * y + m[6] * z,
                                 m[8] * x + m[9] * y + m[10] * z))
            self.idx.extend(i + base for i in mesh.nodeIndices)
            base += len(c) // 3
        info.update(v0=v0, nv=len(self.pos) // 3 - v0, i0=i0, ni=len(self.idx) - i0,
                    bbox=[round(v, 3) for v in lo + hi])
        self.items.append(info)
        return lo, hi


def afficheur(sortie, occ, m, qualite, qualite_arriere, tout):
    """Face de l'afficheur : Body1 (bloc), Body2 (fine couche de face) face par face ; `tout` : et le reste."""
    comp = occ.component
    bloc = comp.bRepBodies.itemByName('Body1')
    sortie.ajoute([calcule(bloc, qualite)], m, dict(occ=occ.fullPathName, body='Body1', part='bloc',
                                           app=bloc.appearance.name, rgb=couleur(bloc.appearance)))
    face = comp.bRepBodies.itemByName('Body2')
    reste = []
    n = 0
    for f in face.faces:
        seg = f.appearance and f.appearance.name == 'Segments jaunes'
        plan = adsk.core.Plane.cast(f.geometry)
        if seg and plan and abs(plan.normal.z) > 0.99:  # fond des segments, 0,08 sous la face
            n += 1
            sortie.ajoute([calcule(f, qualite)], m, dict(occ=occ.fullPathName, body='seg%03d' % n, part='segment',
                                                app=f.appearance.name, rgb=couleur(f.appearance)))
        else:
            reste.append(calcule(f, qualite))
    sortie.ajoute(reste, m, dict(occ=occ.fullPathName, body='Body2', part='face', app=face.appearance.name,
                                 rgb=couleur(face.appearance)))
    if tout:
        for b in comp.bRepBodies:
            if b.name not in ('Body1', 'Body2') and b.isVisible:
                sortie.ajoute([calcule(b, qualite_arriere)], m, dict(occ=occ.fullPathName, body=b.name, part='arriere',
                                                                     app=b.appearance.name, rgb=couleur(b.appearance)))
    return n


def exporte(dossier, skip, qualite, qualite_carte, tout, masquees=()):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    assert doc.name.startswith('claudometre'), doc.name
    d = adsk.fusion.Design.cast(app.activeProduct)
    root = d.rootComponent
    out = os.path.join(os.environ['TEMP'], 'claudemetre', 'export', dossier)
    os.makedirs(out, exist_ok=True)
    s = Sortie()
    ecart = 0.0
    segments = 0
    poses = {}
    for i in range(root.allOccurrences.count):
        o = root.allOccurrences.item(i)
        top = o.fullPathName.split('+')[0]
        force = top in masquees
        if o.fullPathName.startswith(skip) or not (o.isVisible or force):
            continue
        m = o.transform2.asArray()
        if '+' not in o.fullPathName or 'connecteur_LP-16' in o.fullPathName:
            poses[o.fullPathName] = list(m)
        if top.startswith('afficheur'):
            segments = afficheur(s, o, m, qualite, qualite_carte, tout)
            continue
        for j in range(o.bRepBodies.count):
            b = o.bRepBodies.item(j)
            if not (b.isVisible or (force and b.isLightBulbOn)):
                continue
            q = qualite_carte if top.startswith('mrd076a') else qualite
            lo, hi = s.ajoute([calcule(b.nativeObject or b, q)], m,
                              dict(occ=o.fullPathName, body=b.name, part='corps',
                                   app=b.appearance.name if b.appearance else None, rgb=couleur(b.appearance)))
            bb = b.boundingBox
            ref = [bb.minPoint.x * 10, bb.minPoint.y * 10, bb.minPoint.z * 10,
                   bb.maxPoint.x * 10, bb.maxPoint.y * 10, bb.maxPoint.z * 10]
            e = max(abs(a - c) for a, c in zip(lo + hi, ref))
            if e > 1:
                print('écart %.2f mm : %s %s' % (e, o.fullPathName, b.name))
            ecart = max(ecart, e)
    with open(os.path.join(out, 'claudometre.bin'), 'wb') as f:
        s.pos.tofile(f)
        s.nor.tofile(f)
        s.idx.tofile(f)
    info = dict(version=doc.dataFile.versionNumber, non_enregistre=doc.isModified, nv=len(s.pos) // 3,
                ni=len(s.idx), poses=poses, corps=s.items)
    with open(os.path.join(out, 'claudometre.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=0)
    print('v%s, %d corps, %d segments, %d sommets, %d triangles, écart max / boîtes Fusion %.3f mm'
          % (info['version'], len(s.items), segments, info['nv'], info['ni'] // 3, ecart))


def run(ctx):
    exporte('blender', SKIP, Q.VeryHighQualityTriangleMesh, Q.VeryHighQualityTriangleMesh, False)


def complet(ctx):
    exporte('web', ('patron',), 0.006, 0.02, True, PLAQUES)
