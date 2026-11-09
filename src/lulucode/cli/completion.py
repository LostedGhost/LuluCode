"""Autocomplétion de la saisie de session, façon Claude Code.

Taper « / » ouvre un menu des commandes et skills disponibles ; la
saisie continue filtre la liste ; flèches haut/bas naviguent, Tab ou
Entrée complète. Implémenté avec le Completer de prompt_toolkit : le
menu s'affiche sous l'invite, style LuluCode.
"""

from __future__ import annotations

from collections.abc import Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

_DESCRIPTIONS = {
    "/aide": "affiche la liste des commandes",
    "/exit": "termine la session (message d'adieu possible : « /exit merci »)",
    "/mode": "affiche ou change le mode de permission (normal, auto, bypass, strict, lecture-seule)",
    "/quit": "termine la session",
    "/quitter": "termine la session",
    "/skill": "liste les skills, en montre un, ou exécute une tâche guidée par un skill",
    "exit": "termine la session (message d'adieu possible)",
    "quit": "termine la session",
    "quitter": "termine la session",
}


class CompleterSession(Completer):
    """Complète `/commande [argument]` et les noms de skills."""

    def __init__(self, skills: Iterable[str] = ()) -> None:
        self._skills = list(skills)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        texte = document.text_before_cursor.lstrip()
        if not texte.startswith("/"):
            return  # complétion seulement sur les commandes slash

        morceaux = texte.split(maxsplit=1)
        commande = morceaux[0].lower()

        if len(morceaux) == 1:
            # On complète le nom de commande.
            for nom in sorted(_DESCRIPTIONS):
                if nom.startswith(commande):
                    yield Completion(
                        nom,
                        start_position=-len(document.get_word_before_cursor(WORD=True) or ""),
                        display=nom,
                        display_meta=_DESCRIPTIONS[nom],
                    )
            return

        # Arguments de /skill : les noms de skills.
        if commande == "/skill":
            fragment = morceaux[1]
            for nom in self._skills:
                if nom.startswith(fragment):
                    yield Completion(
                        nom,
                        start_position=-len(fragment),
                        display=f"/skill {nom}",
                        display_meta="skill",
                    )


def completions_disponibles(zone) -> CompleterSession:
    """Construit le completer pour cette session (skills du projet+user)."""
    noms: list[str] = []
    try:
        from lulucode.core.skills import decouvre_skills

        noms = [s.name for s in decouvre_skills(zone)]
    except Exception:
        pass  # pas de skills : la complétion reste fonctionnelle
    return CompleterSession(noms)
