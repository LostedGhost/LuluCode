"""Outils de fichiers : lire, écrire, lister, chercher.

Tout chemin est résolu et vérifié contre la zone de travail (liens
symboliques compris) avant tout accès. Un accès extérieur est de niveau 3.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ResultatLecture:
    """Contenu d'un fichier lu, ou une erreur explicite."""

    ok: bool
    contenu: str
    erreur: str = ""


def verifier_zone(chemin: Path, zone: Path) -> str | None:
    """Renvoie une erreur si `chemin` sort de `zone`, None sinon."""
    from lulucode.permissions.moteur import resous_dans_zone

    if not resous_dans_zone(chemin, zone):
        return f"chemin hors de la zone de travail : {chemin}"
    return None


def lire_fichier(chemin: Path, zone: Path, *, taille_max: int = 200_000) -> ResultatLecture:
    """Lit un fichier texte dans la zone de travail."""
    if err := verifier_zone(chemin, zone):
        return ResultatLecture(False, "", err)
    if not chemin.is_file():
        return ResultatLecture(False, "", f"fichier introuvable : {chemin}")
    try:
        contenu = chemin.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return ResultatLecture(False, "", f"lecture impossible : {e}")
    if len(contenu) > taille_max:
        contenu = contenu[:taille_max] + f"\n… (tronqué à {taille_max} caractères)"
    return ResultatLecture(True, contenu)


def lister_dossier(chemin: Path, zone: Path) -> ResultatLecture:
    """Liste le contenu d'un dossier de la zone de travail."""
    if err := verifier_zone(chemin, zone):
        return ResultatLecture(False, "", err)
    if not chemin.is_dir():
        return ResultatLecture(False, "", f"dossier introuvable : {chemin}")
    try:
        entrees = sorted(chemin.iterdir(), key=lambda p: (p.is_file(), p.name))
        lignes = [f"{e.name}/" if e.is_dir() else e.name for e in entrees]
    except OSError as e:
        return ResultatLecture(False, "", f"liste impossible : {e}")
    return ResultatLecture(True, "\n".join(lignes))


def chercher_dans_code(
    motif: str, zone: Path, *, glob: str = "**/*", taille_max_lignes: int = 50
) -> ResultatLecture:
    """Cherche un motif (insensible à la casse) dans les fichiers de la zone."""
    correspondances: list[str] = []
    try:
        fichiers = [f for f in zone.glob(glob) if f.is_file()]
    except OSError as e:
        return ResultatLecture(False, "", f"recherche impossible : {e}")
    for fichier in fichiers:
        if err := verifier_zone(fichier, zone):
            continue
        try:
            texte = fichier.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for num, ligne in enumerate(texte.splitlines(), start=1):
            if motif.lower() in ligne.lower():
                correspondances.append(f"{fichier.relative_to(zone)}:{num}: {ligne.strip()}")
                if len(correspondances) >= taille_max_lignes:
                    correspondances.append("… (résultats tronqués)")
                    return ResultatLecture(True, "\n".join(correspondances))
    if not correspondances:
        return ResultatLecture(True, "aucune correspondance")
    return ResultatLecture(True, "\n".join(correspondances))


def calculer_diff(ancien: str, nouveau: str, nom: str = "fichier") -> str:
    """Diff unifié entre l'ancien et le nouveau contenu d'un fichier."""
    lignes_ancien = ancien.splitlines(keepends=True)
    lignes_nouveau = nouveau.splitlines(keepends=True)
    diff = difflib.unified_diff(
        lignes_ancien, lignes_nouveau, fromfile=f"a/{nom}", tofile=f"b/{nom}"
    )
    return "".join(diff) or "aucun changement"


@dataclass(slots=True)
class ResultatEcriture:
    """Résultat d'une écriture : le diff à montrer et l'état."""

    ok: bool
    diff: str
    erreur: str = ""


def ecrire_fichier(
    chemin: Path, contenu: str, zone: Path, *, autorise: bool
) -> ResultatEcriture:
    """Écrit un fichier dans la zone, mais seulement si c'est autorisé.

    L'appel (que l'agent a déjà passé par le moteur de permissions) doit
    avoir reçu une autorisation explicite : `autorise=False` ne modifie rien.
    """
    if not autorise:
        return ResultatEcriture(False, "", "écriture refusée par les permissions")
    if err := verifier_zone(chemin, zone):
        return ResultatEcriture(False, "", err)
    ancien = chemin.read_text(encoding="utf-8", errors="replace") if chemin.is_file() else ""
    diff = calculer_diff(ancien, contenu, chemin.name)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding="utf-8")
    except OSError as e:
        return ResultatEcriture(False, diff, f"écriture impossible : {e}")
    return ResultatEcriture(True, diff)
