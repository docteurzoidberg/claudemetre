"""Export des cadrans à imprimer : un STL binaire en mm par
composant (fond, echelle, zone, texte) de chaque variante fond-jauge-*, dans
%TEMP%/claudemetre/export/<variante>/, plus export.json (version, volumes,
couleurs des apparences).
Ensuite, côté WSL : uv run cadran_3mf.py (design/fusion) écrit les 3MF.

Une variante déjà ouverte est exportée telle quelle (même non enregistrée,
signalé dans export.json) ; sinon sa dernière version enregistrée est ouverte
en arrière-plan, puis refermée. S'arrête sur une dérivation périmée
(fond-jauge enregistré depuis) ou une fonction en erreur : ces cas se règlent
dans Fusion, par l'utilisateur, avant l'export."""
import json
import os
import shutil
import adsk.core, adsk.fusion

DOSSIER = "claudometre"
VARIANTES = ("fond-jauge-session", "fond-jauge-semaine")


def _fichiers(app):
    dossier = app.data.activeProject.rootFolder.dataFolders.itemByName(DOSSIER)
    return {dossier.dataFiles.item(i).name: dossier.dataFiles.item(i) for i in range(dossier.dataFiles.count)}


def _rgb(body):
    """Couleur de l'apparence « PLA <couleur> » posée par variante()."""
    a = body.appearance
    for i in range(a.appearanceProperties.count if a else 0):
        p = a.appearanceProperties.item(i)
        if isinstance(p, adsk.core.ColorProperty) and p.id in ("opaque_albedo", "generic_diffuse") and p.value:
            return [p.value.red, p.value.green, p.value.blue]
    return None


def _export(doc, dest):
    d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    tl = d.timeline
    bad = [tl.item(i).name for i in range(tl.count) if tl.item(i).healthState != 0]
    if not doc.isUpToDate:
        raise RuntimeError(f"{doc.name} : dérivation périmée, « Mettre à jour » puis enregistrer la variante")
    if bad:
        raise RuntimeError(f"{doc.name} : fonctions en erreur {bad}")
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    em = d.exportManager
    comps = {}
    for occ in d.rootComponent.occurrences:
        name = occ.component.name
        opt = em.createSTLExportOptions(occ, os.path.join(dest, name + ".stl"))
        opt.isBinaryFormat = True
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        opt.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        em.execute(opt)
        bodies = list(occ.component.bRepBodies)
        comps[name] = {"corps": len(bodies), "volume": round(sum(b.volume for b in bodies) * 1000, 3),
                       "rgb": _rgb(bodies[0])}
    return {"version": doc.dataFile.versionNumber if doc.dataFile else None,
            "non_enregistre": doc.isModified, "composants": comps}


def run(ctx):
    app = adsk.core.Application.get()
    out = os.path.join(os.environ["TEMP"], "claudemetre", "export")
    ouverts = {doc.name: doc for doc in app.documents}
    modele = ouverts.get("fond-jauge")
    manifest = {"avertissements": []}
    if modele and modele.isModified:
        manifest["avertissements"].append("fond-jauge modifié et non enregistré : les variantes ne le voient pas")
    fichiers = None
    for nom in VARIANTES:
        doc = ouverts.get(nom)
        if doc is None:
            fichiers = fichiers or _fichiers(app)
            doc = app.documents.open(fichiers[nom], False)
        try:
            manifest[nom] = _export(doc, os.path.join(out, nom))
        finally:
            if nom not in ouverts:
                doc.close(False)
        if manifest[nom]["non_enregistre"]:
            manifest["avertissements"].append(f"{nom} exporté avec des modifications non enregistrées")
    with open(os.path.join(out, "export.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    for nom in VARIANTES:
        m = manifest[nom]
        print(f"{nom} v{m['version']} : " + ", ".join(f"{k} {c['corps']} corps {c['volume']} mm³"
                                                    for k, c in m["composants"].items()))
    for a in manifest["avertissements"]:
        print("ATTENTION :", a)
