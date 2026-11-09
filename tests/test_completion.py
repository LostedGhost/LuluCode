"""Tests du Completer de session (menu /commandes et skills)."""

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from lulucode.cli.completion import CompleterSession


def complete(completer: CompleterSession, texte: str) -> list[str]:
    doc = Document(texte, len(texte))
    return [c.text for c in completer.get_completions(doc, CompleteEvent())]


class TestCommandes:
    def test_slash_seul_propose_tout(self):
        completer = CompleterSession()
        resultats = complete(completer, "/")
        assert "/aide" in resultats
        assert "/mode" in resultats
        assert "/skill" in resultats

    def test_prefixe_filtre(self):
        completer = CompleterSession()
        assert complete(completer, "/mo") == ["/mode"]

    def test_prefixe_inconnu_vide(self):
        assert complete(CompleterSession(), "/zzz") == []

    def test_exit_sans_slash_ne_complete_pas(self):
        """La complétion est réservée aux commandes slash ; un mot nu
        (« exit ») n'ouvre pas le menu (Claude Code pareil).
        """
        completer = CompleterSession()
        assert complete(completer, "exit") == []

    def test_variantes_sortie_slash_completees(self):
        completer = CompleterSession()
        resultats = complete(completer, "/qu")
        assert set(resultats) == {"/quit", "/quitter"}

    def test_display_meta_present(self):
        completer = CompleterSession()
        doc = Document("/", 1)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert all(c.display_meta for c in completions), \
            "chaque commande doit porter sa description pour le menu"


class TestSkills:
    def test_skills_completes_apres_slash_skill(self):
        completer = CompleterSession(["revue", "refactor"])
        resultats = complete(completer, "/skill r")
        assert set(resultats) == {"revue", "refactor"}

    def test_skill_exact(self):
        completer = CompleterSession(["revue"])
        assert "revue" in complete(completer, "/skill re")

    def test_aucun_skill(self):
        assert complete(CompleterSession(), "/skill a") == []
