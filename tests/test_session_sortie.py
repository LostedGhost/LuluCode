"""Tests : sortie de session par « exit », curseur, styles d'état."""

import pytest

from lulucode.cli.main import veut_sortir


class TestSortieSession:
    """« exit » sous n'importe quelle forme coupe l'agent."""

    @pytest.mark.parametrize("saisie", [
        "exit", "Exit", "EXIT", "eXiT",
        "  exit  ", "\texit\n",
        "quit", "Quit", "  quit ",
        "quitter", "Quitter",
        "/exit", "/quit", "/quitter",
    ])
    def test_formes_acceptees(self, saisie):
        assert veut_sortir(saisie) is True

    @pytest.mark.parametrize("saisie", [
        "", "   ", "exite", "exit2", "exit; rm -rf /", "sortir maintenant",
        "lire le fichier", "/aide",
    ])
    def test_formes_refusees(self, saisie):
        assert veut_sortir(saisie) is False

    def test_exit_ne_lance_pas_agent(self):
        """Le seul mot « exit » suivi d'autre chose n'est pas une sortie."""
        assert veut_sortir("exit maintenant") is False


class TestRendu:
    """La ligne d'état est gris clair, le texte de l'agent blanc gras."""

    @pytest.fixture()
    def rendu(self):
        rich = pytest.importorskip("rich")
        import io

        from lulucode.cli.render import RenduRiche
        from rich.console import Console

        r = RenduRiche()
        buf = io.StringIO()
        r.console = Console(file=buf, force_terminal=True, width=120, highlight=False)
        return r, buf

    def test_etat_tout_gris(self, rendu):
        r, buf = rendu
        r.etat("0.1.0", "local", "normal", "C:/u")
        brut = buf.getvalue()
        # Pas de gras cyan sur le titre : gris unique partout.
        assert "bold #22d3ee" not in brut
        # Rich convertit le hex en ANSI 90 (gris clair) : gras présent.
        assert "1;90m" in brut

    def test_texte_agent_blanc(self, rendu):
        r, buf = rendu
        # Le texte de l'agent passe par le rendu Markdown (titres, gras).
        r.texte_agent("# Titre\n\nCorps **gras** de la réponse.")
        brut = buf.getvalue()
        assert "Titre" in brut
        assert "Corps" in brut
        assert "gras" in brut
        # ANSI émis : le Markdown est stylé, pas brut.
        assert chr(27) in brut

    def test_curseur_n_leve_pas(self, rendu):
        r, buf = rendu
        # La console capturée n'est pas un vrai terminal : aucun effet, aucune erreur.
        r.curseur(True)
        r.curseur(False)

    def test_curseur_sans_rich(self):
        from lulucode.cli.render import RenduSimple

        RenduSimple().curseur(True)  # ne doit rien lever
        RenduSimple().curseur(False)


class TestModuleUpdate:
    """Détecte l'installation et lister les versions n'échoue jamais."""

    def test_detecte_installation(self):
        from lulucode.cli.update import detecte_installation

        inst = detecte_installation()
        assert inst.mode in ("pypi", "local", "editable", "inconnu")

    def test_liste_versions_sans_exception(self):
        from lulucode.cli.update import detecte_installation, liste_versions

        versions = liste_versions(detecte_installation())
        assert isinstance(versions, list)

    def test_veut_sortir_importable_via_main(self):
        from lulucode.cli.main import veut_sortir  # noqa: F401
