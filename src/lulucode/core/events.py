"""Contrat d'événements du cœur de LuluCode.

Le cœur émet des événements et consomme des réponses ; il ne connaît aucune
façade. Le terminal et l'interface web affichent les mêmes événements et
renvoient les mêmes réponses, ce qui garantit des règles identiques.
"""

from __future__ import annotations

import enum
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


class Kind(enum.StrEnum):
    """Types d'événements émis par le cœur."""

    TACHE_DEMARREE = "tache_demarree"
    TEXTE = "texte"
    OUTIL_APPEL = "outil_appel"
    OUTIL_RESULTAT = "outil_resultat"
    DIFF = "diff"
    PERMISSION_DEMANDEE = "permission_demandee"
    PERMISSION_REPONSE = "permission_reponse"
    ERREUR = "erreur"
    PLAFOND = "plafond"
    TACHE_TERMINEE = "tache_terminee"


@dataclass(slots=True)
class Evenement:
    """Un événement du flux, le même pour les deux façades.

    `donnees` contient les champs spécifiques au type (texte, nom d'outil,
    chemin de fichier, ancien/nouveau contenu, etc.).
    """

    type: Kind
    donnees: dict[str, Any] = field(default_factory=dict)
    horodatage: float = field(default_factory=time.time)


PermissionCallback = Callable[[dict[str, Any]], Awaitable[bool]]
"""Reçoit `{"outil", "rationale", "risque", "resume"}` et répond True/False."""


class Emetteur(Protocol):
    """Ce que le cœur attend d'une façade : afficher, rien de plus."""

    def emettre(self, evenement: Evenement) -> None:
        """Notifie la façade d'un événement."""
        ...


class Collecteur:
    """Émetteur minimal qui empile les événements pour les tests."""

    def __init__(self) -> None:
        self.evenements: list[Evenement] = []

    def emettre(self, evenement: Evenement) -> None:
        self.evenements.append(evenement)

    def types(self, *kind: Kind) -> list[Evenement]:
        return [e for e in self.evenements if e.type in kind]

    def textes(self) -> str:
        return "".join(str(e.donnees.get("texte", "")) for e in self.types(Kind.TEXTE))
