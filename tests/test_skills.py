"""Tests des skills au format Claude et des commandes /mode / /skill."""

from pathlib import Path

from lulucode.core.skills import (
    Skill,
    corps_du_skill,
    decouvre_skills,
    liste_pour_modele,
)


def _cree_skill(racine: Path, nom: str, description: str, corps: str = "Instructions.") -> Path:
    dossier = racine / nom
    dossier.mkdir(parents=True)
    chemin = dossier / "SKILL.md"
    chemin.write_text(
        f"---\nname: {nom}\ndescription: {description}\n---\n\n{corps}\n",
        encoding="utf-8",
    )
    return chemin


class TestDecouverte:
    def test_skill_projet_decouvert(self, tmp_path):
        _cree_skill(tmp_path / ".lulucode" / "skills", "revue", "Revue de code soignée")
        skills = decouvre_skills(tmp_path)
        noms = [s.name for s in skills]
        assert "revue" in noms

    def test_champs_frontmatter(self, tmp_path):
        _cree_skill(tmp_path / ".lulucode" / "skills", "revue", "Revue de code", "Corps ici.")
        skill = decouvre_skills(tmp_path)[0]
        assert skill.description == "Revue de code"
        assert "Corps ici." in skill.corps
        assert skill.chemin.endswith("SKILL.md")

    def test_projet_masque_utilisateur(self, tmp_path, monkeypatch):
        _cree_skill(tmp_path / ".lulucode" / "skills", "commun", "version projet")
        _cree_skill(Path.home() / "__test_deco_skills__", "commun", "version utilisateur")
        monkeypatch.setenv("HOME", str(tmp_path))  # ~/.lulucode sous tmp_path
        skills = decouvre_skills(tmp_path)
        assert all(s.description == "version projet" for s in skills if s.name == "commun")

    def test_skill_invalide_ignore(self, tmp_path):
        dossier = tmp_path / ".lulucode" / "skills" / "casse"
        dossier.mkdir(parents=True)
        (dossier / "SKILL.md").write_text("pas de frontmatter", encoding="utf-8")
        assert decouvre_skills(tmp_path) == []

    def test_aucun_skill_acune_erreur(self, tmp_path):
        assert decouvre_skills(tmp_path) == []


class TestInjection:
    def test_liste_vide_ne_produit_rien(self):
        assert liste_pour_modele([]) == ""

    def test_liste_pour_le_modele(self):
        skills = [Skill("revue", "Revue de code", "x/SKILL.md")]
        bloc = liste_pour_modele(skills)
        assert "/skill" in bloc
        assert "revue" in bloc
        assert "Revue de code" in bloc

    def test_corps_du_skill(self, tmp_path):
        _cree_skill(tmp_path / ".lulucode" / "skills", "revue", "Revue", "Le corps complet.")
        skills = decouvre_skills(tmp_path)
        assert "Le corps complet." in corps_du_skill(skills, "revue")

    def test_corps_inconnu_renvoie_none(self):
        assert corps_du_skill([], "fantome") is None


class TestModeEtSortie:
    def test_au_revoir_accepte_message(self):
        """La signature du rendu accepte un message facultatif."""
        rich = __import__("importlib").import_module("importlib")
        from lulucode.cli.render import RenduSimple

        rs = RenduSimple()  # click est requis ; vérifions la signature
        import inspect

        params = inspect.signature(rs.au_revoir).parameters
        assert "message" in params
