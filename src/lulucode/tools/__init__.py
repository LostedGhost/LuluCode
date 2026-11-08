"""Outils de LuluCode : fichiers, commandes, recherche de code.

Chaque outil déclare son niveau de risque ; l'exécution passe toujours
par le moteur de permissions avant de toucher au disque.
"""

from lulucode.tools.fichiers import (
    calculer_diff,
    chercher_dans_code,
    ecrire_fichier,
    lister_dossier,
    lire_fichier,
)

__all__ = [
    "calculer_diff",
    "chercher_dans_code",
    "ecrire_fichier",
    "lister_dossier",
    "lire_fichier",
]
