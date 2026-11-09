"""Tests des modes auto et bypass — les garanties qui les définissent."""

import pytest

from lulucode.permissions.moteur import DecisionValeur, Moteur, Mode, Niveau


class TestModeAuto:
    def test_auto_valide_lecture_sans_confirmation(self):
        d = Moteur(mode=Mode.AUTO).autoriser("lire_fichier", Niveau.LECTURE)
        assert d.valeur is DecisionValeur.AUTORISE

    def test_auto_valide_ecriture_sans_confirmation(self):
        d = Moteur(mode=Mode.AUTO).autoriser("ecrire_fichier", Niveau.ECRITURE)
        assert d.valeur is DecisionValeur.AUTORISE

    def test_auto_valide_commande_sans_confirmation(self):
        d = Moteur(mode=Mode.AUTO).autoriser("lancer_commande", Niveau.COMMANDE)
        assert d.valeur is DecisionValeur.AUTORISE

    def test_auto_confirme_toujours_le_niveau_3(self):
        """Invariant central du mode auto : rien de destructif sans accord."""
        d = Moteur(mode=Mode.AUTO).autoriser("supprimer", Niveau.DESTRUCTIF)
        assert d.valeur is DecisionValeur.CONFIRMATION
        assert d.valeur is not DecisionValeur.AUTORISE

    def test_auto_commande_simple_valide_seule(self):
        d = Moteur(mode=Mode.AUTO).autoriser_commande("pytest -q")
        assert d.valeur is DecisionValeur.AUTORISE

    def test_auto_rm_rf_attend_toujours(self):
        """Un motif dangereux (niveau 3) n'est jamais auto-validé."""
        d = Moteur(mode=Mode.AUTO).autoriser_commande("rm -rf /")
        assert d.valeur is DecisionValeur.CONFIRMATION

    def test_auto_sudo_attend_toujours(self):
        d = Moteur(mode=Mode.AUTO).autoriser_commande("sudo apt install x")
        assert d.valeur is DecisionValeur.CONFIRMATION


class TestModeBypass:
    def test_bypass_autorise_tout_meme_niveau_3(self):
        d = Moteur(mode=Mode.BYPASS).autoriser("supprimer", Niveau.DESTRUCTIF)
        assert d.valeur is DecisionValeur.AUTORISE

    def test_bypass_autorise_ecriture(self):
        d = Moteur(mode=Mode.BYPASS).autoriser("ecrire_fichier", Niveau.ECRITURE)
        assert d.valeur is DecisionValeur.AUTORISE

    def test_bypass_commande_simple_valide(self):
        d = Moteur(mode=Mode.BYPASS).autoriser_commande("pytest -q")
        assert d.valeur is DecisionValeur.AUTORISE

    def test_bypass_commande_rm_rf_valide(self):
        d = Moteur(mode=Mode.BYPASS).autoriser_commande("rm -rf /")
        assert d.valeur is DecisionValeur.AUTORISE

    def test_bypass_ne_memorise_pas_le_niveau_3(self):
        """La garantie de session reste : jamais de niveau 3 mémorisé."""
        m = Moteur(mode=Mode.BYPASS)
        with pytest.raises(ValueError):
            m.memoriser_session("supprimer", Niveau.DESTRUCTIF)
