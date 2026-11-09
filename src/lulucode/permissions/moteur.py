"""Moteur de permissions : niveaux de risque, modes, décisions mémorisées."""

from __future__ import annotations

import enum
import fnmatch
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path


class Niveau(enum.IntEnum):
    """Niveau de risque d'une action, de la lecture à la destruction."""

    LECTURE = 0
    ECRITURE = 1
    COMMANDE = 2
    DESTRUCTIF = 3


class Mode(enum.StrEnum):
    """Mode de fonctionnement global de la session."""

    NORMAL = "normal"
    AUTO = "auto"
    BYPASS = "bypass"
    STRICT = "strict"
    LECTURE_SEULE = "lecture-seule"


class DecisionValeur(enum.StrEnum):
    """Décision rendue par le moteur."""

    AUTORISE = "autorise"
    CONFIRMATION = "confirmation"
    REFUSE = "refuse"


@dataclass(slots=True)
class Decision:
    """Décision du moteur, émise comme événement vers la façade."""

    valeur: DecisionValeur
    niveau: Niveau
    raison: str


@dataclass
class Moteur:
    """Décide si une action est autorisée, à confirmer ou refusée.

    Règles invariantes :
    - le mode `strict` exige une confirmation pour tout, lectures comprises ;
    - le mode `lecture-seule` refuse écriture, commande et destruction ;
    - le mode `auto` valide seul les actions de niveau 0 à 2, mais une
      action de niveau 3 (destructive) attend toujours l'utilisateur ;
    - le mode `bypass` exécute tout sans validation ;
    - une action de niveau 3 n'est jamais mémorisée pour la session ;
    - les motifs dangereux restent de niveau 3 même si la commande est « sûre ».
    """

    mode: Mode = Mode.NORMAL
    sures: list[str] = field(default_factory=list)
    _session: set[tuple[str, Niveau]] = field(default_factory=set, repr=False)

    _MOTIFS_DANGEREUX = [
        r"\brm\s+[^\n]*-[a-zA-Z]*r[a-zA-Z]*f",
        r"\brm\s+[^\n]*-[a-zA-Z]*f[a-zA-Z]*r",
        r"\bsudo\b",
        r"\bgit\s+push\b[^\n]*(-f|--force)",
        r"\bmkfs\b",
        r">\s*/dev/sd",
        r"\b(curl|wget)\b[^\n]*\|\s*(ba|z)?sh\b",
        r"\bdel\s+/[sq]",
        r"\brd\s+/s",
    ]

    def autoriser(
        self,
        outil: str,
        niveau: Niveau,
        detail: str = "",
        *,
        pour_la_session: bool = False,
    ) -> Decision:
        """Décide du sort d'une action générique."""
        if self.mode is Mode.BYPASS:
            return Decision(DecisionValeur.AUTORISE, niveau, "mode bypass")

        if self.mode is Mode.AUTO and niveau < Niveau.DESTRUCTIF:
            return Decision(
                DecisionValeur.AUTORISE, niveau, "mode auto (niveau ≤ 2 validé seul)"
            )
        # En mode auto, le niveau 3 retombe sur le comportement normal.

        if pour_la_session and (outil, niveau) in self._session and niveau < Niveau.DESTRUCTIF:
            return Decision(DecisionValeur.AUTORISE, niveau, "déjà autorisé pour la session")

        if self.mode is Mode.STRICT:
            return Decision(DecisionValeur.CONFIRMATION, niveau, "mode strict")

        if self.mode is Mode.LECTURE_SEULE and niveau >= Niveau.ECRITURE:
            return Decision(DecisionValeur.REFUSE, niveau, "mode lecture-seule")

        if niveau is Niveau.LECTURE:
            return Decision(DecisionValeur.AUTORISE, niveau, "lecture dans la zone")

        if niveau is Niveau.DESTRUCTIF:
            return Decision(DecisionValeur.CONFIRMATION, niveau, "action destructrice")

        return Decision(DecisionValeur.CONFIRMATION, niveau, "à confirmer")

    def memoriser_session(self, cle: str, niveau: Niveau) -> None:
        """Mémorise une autorisation pour la session (jamais le niveau 3)."""
        if niveau >= Niveau.DESTRUCTIF:
            raise ValueError("Une action de niveau 3 ne peut jamais être autorisée pour la session.")
        self._session.add((cle, niveau))

    def verifier_commande(self, commande: str) -> tuple[Niveau, str]:
        """Évalue une commande shell : niveau de risque et raison.

        Une commande composée (enchaînements, redirections, substitutions
        de commande) est traitée au niveau supérieur, car analyser un shell
        de façon sûre est difficile.
        """
        strippee = commande.strip()
        if not strippee:
            return Niveau.DESTRUCTIF, "commande vide"

        for motif in self._MOTIFS_DANGEREUX:
            if re.search(motif, strippee):
                return Niveau.DESTRUCTIF, f"motif dangereux ({motif})"

        composee = any(token in strippee for token in ("&&", "||", ";", "`", "$(", "|", ">"))
        if composee:
            return Niveau.COMMANDE, "commande composée"

        try:
            morceaux = shlex.split(strippee)
        except ValueError:
            return Niveau.DESTRUCTIF, "commande non analysable"

        if not morceaux or morceaux[0] not in self._BINAIRES_CONNUES:
            return Niveau.DESTRUCTIF, "commande inconnue"

        return Niveau.COMMANDE, "commande simple"

    def autoriser_commande(self, commande: str, *, pour_la_session: bool = False) -> Decision:
        """Décide du sort d'une commande shell, en tenant compte des préfixes sûrs."""
        niveau, raison = self.verifier_commande(commande)

        if self.mode is Mode.STRICT:
            return Decision(DecisionValeur.CONFIRMATION, niveau, "mode strict")
        if self.mode is Mode.LECTURE_SEULE:
            return Decision(DecisionValeur.REFUSE, niveau, "mode lecture-seule")
        if self.mode is Mode.BYPASS:
            return Decision(DecisionValeur.AUTORISE, niveau, "mode bypass")
        if self.mode is Mode.AUTO and niveau < Niveau.DESTRUCTIF:
            return Decision(
                DecisionValeur.AUTORISE, niveau, f"mode auto ({raison})"
            )
        # En mode auto, une commande de niveau 3 suit le chemin normal.

        strippee = commande.strip()
        if niveau is not Niveau.DESTRUCTIF and self.sures:
            for regle in self.sures:
                if fnmatch.fnmatch(strippee, regle + "*") or fnmatch.fnmatch(strippee, regle):
                    if (strippee, Niveau.COMMANDE) in self._session or pour_la_session:
                        return Decision(
                            DecisionValeur.AUTORISE, niveau,
                            f"commande sûre autorisée pour la session ({raison})",
                        )
                    return Decision(
                        DecisionValeur.CONFIRMATION, niveau,
                        f"commande sûre, première demande ({raison})",
                    )

        if (
            pour_la_session
            and (strippee, Niveau.COMMANDE) in self._session
            and niveau < Niveau.DESTRUCTIF
        ):
            return Decision(DecisionValeur.AUTORISE, niveau, "déjà autorisé pour la session")

        return Decision(DecisionValeur.CONFIRMATION, niveau, raison)

    _BINAIRES_CONNUES = {
        "ls", "cat", "head", "tail", "grep", "find", "pwd", "echo", "wc", "which",
        "git", "python", "python3", "pip", "pytest", "ruff", "mypy", "node", "npm",
        "make", "cargo", "go", "tree", "diff", "sort", "uniq",
    }


def resous_dans_zone(chemin: Path, zone: Path) -> bool:
    """True si `chemin` résolu (liens symboliques compris) reste dans `zone`.

    Fonction utilitaire exportée pour les outils de fichiers : tout accès
    extérieur à la zone de travail est de niveau 3.
    """
    try:
        chemin_resolu = chemin.resolve(strict=False)
        zone_resolue = zone.resolve(strict=False)
    except OSError:
        return False
    return chemin_resolu == zone_resolue or zone_resolue in chemin_resolu.parents
