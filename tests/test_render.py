"""Tests du rendu terminal (gabarits des SVG du README)."""

import pytest

rich = pytest.importorskip("rich")

from lulucode.cli.render import (
    BLEU,
    BORDE,
    CYAN,
    JAUNE,
    PANNEAU,
    ROUGE,
    SECONDAIRE,
    VERT,
    RenduRiche,
    cree_rendu,
)
from rich.console import Console
from rich.theme import Theme


@pytest.fixture()
def rendu_capte():
    """RenduRiche avec console capturée (force_terminal, sans écran)."""
    r = RenduRiche()
    buf = io_string = __import__("io").StringIO()
    r.console = Console(
        file=buf,
        force_terminal=True,
        width=100,
        highlight=False,
        theme=Theme({
            "texte": "#e6edf3", "gris": SECONDAIRE, "cyan": CYAN, "violet": "#a78bfa",
            "vert": VERT, "bleu": BLEU, "jaune": JAUNE, "rouge": ROUGE, "etat": SECONDAIRE,
        }),
    )
    return r, buf


def texte_sans_ansi(s: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", s)


class TestGabaritsSVG:
    def test_ligne_etat_comme_svg(self, rendu_capte):
        r, buf = rendu_capte
        r.etat("0.1.0", "local", "normal", "C:/projets/api")
        texte = texte_sans_ansi(buf.getvalue())
        assert "LuluCode 0.1.0" in texte
        assert "profil local" in texte
        assert "mode normal" in texte
        assert "dossier C:/projets/api" in texte
        assert chr(27) in buf.getvalue(), "les couleurs ANSI doivent être émises"

    def test_etiquette_outil_niveau_0(self, rendu_capte):
        r, buf = rendu_capte
        r.outil("lire_fichier", "src/factures.py")
        texte = texte_sans_ansi(buf.getvalue())
        assert "[lecture] src/factures.py" in texte

    def test_etiquette_outil_niveau_1(self, rendu_capte):
        r, buf = rendu_capte
        r.outil("ecrire_fichier", "tests/x.py")
        assert "[écriture] tests/x.py" in texte_sans_ansi(buf.getvalue())

    def test_etiquette_outil_niveau_2(self, rendu_capte):
        r, buf = rendu_capte
        r.outil("lancer_commande", "pytest -q")
        assert "[commande] pytest -q" in texte_sans_ansi(buf.getvalue())

    def test_diff_panneau_avec_lignes_plus(self, rendu_capte):
        r, buf = rendu_capte
        r.diff("tests/x.py", "@@ -0,0 +1,1 @@\n+x = 1")
        texte = texte_sans_ansi(buf.getvalue())
        assert "+x = 1" in texte
        assert "tests/x.py" in texte

    def test_contenu_crochets_ne_casse_pas_le_style(self, rendu_capte):
        """Un chemin ou un argument contenant [qqch] ne doit pas casser Rich."""
        r, buf = rendu_capte
        r.outil("lire_fichier", "[weird]/fichier.txt")
        texte = texte_sans_ansi(buf.getvalue())
        assert "[weird]/fichier.txt" in texte
        assert chr(27) in buf.getvalue(), "l'étiquette reste colorée"

    def test_tache_terminee_reste_silencieuse(self, rendu_capte):
        """L'émetteur n'affiche rien pour OUTIL_RESULTAT (redondant)."""
        from lulucode.core.events import Evenement, Kind

        r, buf = rendu_capte
        e = Evenement(Kind.OUTIL_RESULTAT, {"outil": "lire_fichier", "resultat": "x"})
        from lulucode.cli.main import _EmetteurTerminal

        _EmetteurTerminal(r).emettre(e)
        assert buf.getvalue() == ""


def test_rendu_sans_rich_existe():
    """Sans Rich, cree_rendu renvoie le rendu sobre (monochrome)."""
    from lulucode.cli.render import RenduSimple

    rs = RenduSimple()
    assert hasattr(rs, "outil")
    assert hasattr(rs, "diff")
