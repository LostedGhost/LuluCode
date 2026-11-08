"""Outil de commandes : exécution shell sous permission et plafonds."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ResultatCommande:
    """Sortie d'une commande lancée dans la zone de travail."""

    ok: bool
    sortie: str
    code_retour: int = 0
    duree_s: float = 0.0
    erreur: str = ""


def lance_commande(
    commande: str,
    zone: Path,
    *,
    autorise: bool,
    delai_s: int = 60,
    sortie_max: int = 20_000,
) -> ResultatCommande:
    """Lance une commande si elle a été autorisée, capture la sortie.

    Sans autorisation explicite (`autorise=False`), rien n'est lancé :
    c'est le moteur de permissions qui décide, jamais l'outil.
    """
    if not autorise:
        return ResultatCommande(False, "", erreur="commande refusée par les permissions")
    try:
        procesus = subprocess.run(
            commande,
            shell=True,
            cwd=zone,
            capture_output=True,
            text=True,
            timeout=delai_s,
        )
    except subprocess.TimeoutExpired:
        return ResultatCommande(False, "", erreur=f"délai dépassé ({delai_s} s)")
    except OSError as e:
        return ResultatCommande(False, "", erreur=f"lancement impossible : {e}")

    sortie = (procesus.stdout + procesus.stderr).strip()
    if len(sortie) > sortie_max:
        sortie = sortie[:sortie_max] + f"\n… (tronqué à {sortie_max} caractères)"
    return ResultatCommande(
        ok=procesus.returncode == 0,
        sortie=sortie,
        code_retour=procesus.returncode,
        duree_s=0.0,
    )
