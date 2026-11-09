"""Tests du system prompt chargé depuis systeme/prompt.md."""

from pathlib import Path

from lulucode.core.agent import construit_prompt_systeme


class TestChargement:
    def test_le_fichier_se_charge(self):
        p = construit_prompt_systeme()
        # Sections clés du prompt fourni.
        assert "Identité et mission" in p
        assert "Modes de permission" in p
        assert "Rappel final" in p

    def test_variables_substituees(self):
        p = construit_prompt_systeme(zone=Path("C:/x/demo"), mode="strict")
        assert "C:\\x\\demo" in p
        assert "strict" in p
        assert "Windows" in p or "Linux" in p or "Darwin" in p
        # Aucune variable restée non substituée.
        assert "{{" not in p

    def test_note_modes_reels(self):
        """Le prompt cite auto/bypass : la note aligne sur les modes réels."""
        p = construit_prompt_systeme()
        assert "Modes réellement disponibles" in p
        assert "`normal`" in p
        assert "`strict`" in p
        assert "`lecture-seule`" in p

    def test_distinct_par_mode(self):
        a = construit_prompt_systeme(mode="normal")
        b = construit_prompt_systeme(mode="lecture-seule")
        assert a != b
