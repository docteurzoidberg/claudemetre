"""Chemins propres au poste, lus dans prive.env à la racine du dépôt (hors Git)."""
import shlex
from pathlib import Path

FICHIER = Path(__file__).resolve().parents[2] / "prive.env"


def valeur(cle):
    for ligne in FICHIER.read_text(encoding="utf-8").splitlines():
        nom, _, reste = ligne.partition("=")
        if nom.strip() == cle:
            return shlex.split(reste)[0]
    raise KeyError(f"{cle} absent de {FICHIER}")


WIN_TEMP = Path(valeur("WIN_TEMP"))
