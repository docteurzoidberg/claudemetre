#!/usr/bin/env python3
"""Page autonome de maquette/ pour l'artefact claude.ai : three.js et le code en IIFE, modèle en base64, tout inline.

Usage : python3 page_autonome.py <dossier de travail>
  → <dossier>/eclate.html, à publier, et <dossier>/test.html, à servir avec serve_csp.py.

Un artefact n'applique pas l'importmap et refuse les .glb : maquette/ les garde pour GitHub Pages, cette page s'en
passe. three.js s'installe dans le dossier de travail, à la version de l'importmap de maquette/index.html.
"""
import base64
import re
import subprocess
import sys
from pathlib import Path

ESBUILD = "0.25.10"
M = Path(__file__).resolve().parents[3] / "maquette"
CHARGE = '''{
  const s = atob(window.__modele);
  const o = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) o[i] = s.charCodeAt(i);
  new GLTFLoader().parse(o.buffer, "", prepare, (erreur) => {
    console.error(erreur);
    attente.textContent = "Le modèle n'a pas pu être chargé.";
  });
}
'''

W = Path(sys.argv[1]).resolve()
W.mkdir(parents=True, exist_ok=True)
html = (M / "index.html").read_text(encoding="utf-8")
three = re.search(r"three@([\d.]+)/build", html).group(1)
subprocess.run(["npm", "install", "--silent", "--no-audit", "--no-fund", f"three@{three}", f"esbuild@{ESBUILD}"],
               cwd=W, check=True)

js, n = re.subn(r'new GLTFLoader\(\)\.load\(\s*"claudometre\.glb",\s*prepare,.*?\n\);\n', CHARGE,
                (M / "main.js").read_text(encoding="utf-8"), flags=re.S)
assert n == 1, "chargement du modèle introuvable dans main.js"
(W / "main.js").write_text(js, encoding="utf-8")
subprocess.run([str(W / "node_modules/.bin/esbuild"), "main.js", "--bundle", "--format=iife", "--minify",
                "--target=es2022", "--outfile=bundle.js", "--log-level=warning"], cwd=W, check=True)
code = (W / "bundle.js").read_text(encoding="utf-8")
assert "</script" not in code

corps = re.search(r'<body>(.*?)<script type="module"', html, re.S).group(1)
css = (M / "style.css").read_text(encoding="utf-8")
fontes = [f for f in re.findall(r'<link rel="(?:preconnect|stylesheet)"[^>]*>', html) if "style.css" not in f]
tete = ('<title>Claudemètre éclaté</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        + "\n".join(fontes) + "\n<style>\n" + css + "</style>\n")
glb = base64.b64encode((M / "claudometre.glb").read_bytes()).decode()
page = tete + corps + '<script>window.__modele="' + glb + '";</script>\n<script>' + code + "</script>\n"
(W / "eclate.html").write_text(page, encoding="utf-8")

taille = len(page.encode()) / 1e6
print(f"{W / 'eclate.html'} : {taille:.2f} Mo, three {three}")
assert taille < 16, "au-delà de la limite d'un artefact"

# Page de test : celle de claude.ai a une CSP à nonce et un window.claude non configurable
essai = page.replace("<script>", '<script nonce="t">')
(W / "test.html").write_text(
    '<!doctype html><html lang="fr"><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<script nonce="t">Object.defineProperty(window,"claude",{value:{},configurable:false})</script>' + essai,
    encoding="utf-8")
