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
    from lulucode.cli.render import _tableaux_delimites

    _tableaux_delimites()  # applique le style de boîte des tableaux
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
            "markdown.table.header": f"bold {CYAN}", "markdown.table.border": BORDE,
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
        assert "⏺ lecture · src/factures.py" in texte

    def test_etiquette_outil_niveau_1(self, rendu_capte):
        r, buf = rendu_capte
        r.outil("ecrire_fichier", "tests/x.py")
        assert "⏺ écriture · tests/x.py" in texte_sans_ansi(buf.getvalue())

    def test_etiquette_outil_niveau_2(self, rendu_capte):
        r, buf = rendu_capte
        r.outil("lancer_commande", "pytest -q")
        assert "⏺ commande · pytest -q" in texte_sans_ansi(buf.getvalue())

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


TABLEAU_MD = (
    "| Commande | Description |\n"
    "| --- | --- |\n"
    "| lire_fichier | Lit un fichier |\n"
    "| ecrire_fichier | Ecrit un fichier |\n"
    "| lancer_commande | Lance une commande |\n"
)


class TestTableaux:
    def test_rangées_separees_par_une_ligne(self, rendu_capte):
        """Un tableau de 3 rangées trace >= 2 lignes horizontales :
        une sous l'en-tête, une (au moins) entre les rangées.
        """
        r, buf = rendu_capte
        r.texte_agent(TABLEAU_MD)
        texte = texte_sans_ansi(buf.getvalue())
        lignes_horizontales = [
            ligne for ligne in texte.splitlines()
            if ligne.strip() and set(ligne.strip()) <= {"─", "━"}
        ]
        assert len(lignes_horizontales) >= 2, texte

    def test_regles_differentes_entete_vs_rangees(self, rendu_capte):
        """La règle sous l'en-tête est épaisse (━), les séparateurs de
        rangées sont fins (─) : hiérarchie visuelle de l'en-tête.
        """
        r, buf = rendu_capte
        r.texte_agent(TABLEAU_MD)
        texte = texte_sans_ansi(buf.getvalue())
        epaisses = [l for l in texte.splitlines() if l.strip() and set(l.strip()) == {"━"}]
        fines = [l for l in texte.splitlines() if l.strip() and set(l.strip()) == {"─"}]
        assert len(epaisses) >= 1, texte
        assert len(fines) >= 2, texte  # entre chacune des 3 rangées de données

    def test_pas_de_cadre_complet(self, rendu_capte):
        """Pas d'angles pleins ni de bord haut/bas : côtés ouverts, pas
        l'aspect « encadré » de HEAVY_HEAD.
        """
        r, buf = rendu_capte
        r.texte_agent(TABLEAU_MD)
        texte = texte_sans_ansi(buf.getvalue())
        for coin in "┏┓┗┛┌┐└┘":
            assert coin not in texte, f"angle {coin} inattendu"

    def test_colonnes_delimitees_par_barres_verticales(self, rendu_capte):
        """Les colonnes restent délimitées par des │ (lisibilité d'un
        tableau large), contrairement à box=SIMPLE.
        """
        r, buf = rendu_capte
        r.texte_agent(TABLEAU_MD)
        texte = texte_sans_ansi(buf.getvalue())
        colonnes = [l for l in texte.splitlines() if "│" in l]
        assert len(colonnes) >= 3, texte

    def test_en_tete_mise_en_avant_dans_le_theme(self, rendu_capte):
        """Le thème de la console stylise l'en-tête en bold cyan."""
        r, buf = rendu_capte
        r.texte_agent(TABLEAU_MD)
        assert "\x1b[1;96mCommande" in buf.getvalue()

    def test_texte_agent_tableau_dans_blob_texte(self):
        """blob_texte (blocs de la session plein écran) profite du même
        monkey-patch de boîte : les tableaux y sont aussi délimités.
        """
        from lulucode.cli.render import blob_texte, _tableaux_delimites

        _tableaux_delimites()

        buf = __import__("io").StringIO()
        console = Console(file=buf, force_terminal=True, width=100, highlight=False)
        console.print(blob_texte(TABLEAU_MD))
        texte = texte_sans_ansi(buf.getvalue())
        lignes_horizontales = [
            ligne for ligne in texte.splitlines()
            if ligne.strip() and set(ligne.strip()) <= {"─", "━"}
        ]
        assert len(lignes_horizontales) >= 2, texte
