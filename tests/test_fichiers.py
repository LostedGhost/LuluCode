"""Tests des outils de fichiers, en particulier la zone de travail."""

import pytest

from lulucode.tools.fichiers import (
    calculer_diff,
    chercher_dans_code,
    ecrire_fichier,
    lister_dossier,
    lire_fichier,
)


@pytest.fixture()
def zone(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("def total():\n    return 42\n", encoding="utf-8")
    return tmp_path


class TestZone:
    def test_lecture_hors_zone_refusee(self, zone, tmp_path_factory):
        ailleurs = tmp_path_factory.mktemp("ailleurs") / "secret.txt"
        ailleurs.write_text("secret", encoding="utf-8")
        r = lire_fichier(ailleurs, zone)
        assert not r.ok
        assert "hors de la zone" in r.erreur

    def test_ecriture_hors_zone_refusee(self, zone, tmp_path_factory):
        ailleurs = tmp_path_factory.mktemp("ailleurs") / "sortie.txt"
        r = ecrire_fichier(ailleurs, "hack", zone, autorise=True)
        assert not r.ok
        assert "hors de la zone" in r.erreur

    def test_lien_symbolique_ne_sort_pas_de_la_zone(self, zone, tmp_path_factory):
        # Windows : la création d'un lien symbolique demande le privilège
        # SeCreateSymbolicLink ; on sonde puis on passe s'il manque.
        try:
            sonde = tmp_path_factory.mktemp("sonde") / "sonde.txt"
            sonde.write_text("", encoding="utf-8")
            (sonde.parent / "lien_sonde").symlink_to(sonde)
        except OSError:
            pytest.skip("privilège symlink absent sur ce Windows")
        cible = tmp_path_factory.mktemp("hors") / "secret.txt"
        cible.write_text("secret", encoding="utf-8")
        lien = zone / "lien.txt"
        lien.symlink_to(cible)
        r = lire_fichier(lien, zone)
        assert not r.ok
        assert "hors de la zone" in r.erreur


class TestLectureEcriture:
    def test_lire_fichier(self, zone):
        r = lire_fichier(zone / "src" / "module.py", zone)
        assert r.ok
        assert "42" in r.contenu

    def test_lire_inexistant(self, zone):
        r = lire_fichier(zone / "nexistepas.py", zone)
        assert not r.ok
        assert "introuvable" in r.erreur

    def test_lister_dossier(self, zone):
        r = lister_dossier(zone / "src", zone)
        assert r.ok
        assert "module.py" in r.contenu

    def test_ecriture_sans_autorisation_ne_modifie_pas(self, zone):
        cible = zone / "src" / "module.py"
        avant = cible.read_text(encoding="utf-8")
        r = ecrire_fichier(cible, "nouveau", zone, autorise=False)
        assert not r.ok
        assert "refusée" in r.erreur
        assert cible.read_text(encoding="utf-8") == avant

    def test_ecriture_autorisee_produit_diff(self, zone):
        cible = zone / "src" / "module.py"
        r = ecrire_fichier(cible, "def total():\n    return 43\n", zone, autorise=True)
        assert r.ok
        assert "-    return 42" in r.diff
        assert "+    return 43" in r.diff
        assert cible.read_text(encoding="utf-8").endswith("43\n")

    def test_ecriture_cree_les_dossiers_parents(self, zone):
        r = ecrire_fichier(zone / "tests" / "nouveau.txt", "ok", zone, autorise=True)
        assert r.ok
        assert (zone / "tests" / "nouveau.txt").read_text(encoding="utf-8") == "ok"


class TestRecherche:
    def test_chercher_code(self, zone):
        r = chercher_dans_code("total", zone, glob="**/*.py")
        assert r.ok
        assert "module.py:1" in r.contenu

    def test_chercher_sans_resultat(self, zone):
        r = chercher_dans_code("inexistant_partout", zone)
        assert r.ok
        assert "aucune correspondance" in r.contenu


class TestDiff:
    def test_diff_unifie(self):
        d = calculer_diff("a\n", "b\n", "x.txt")
        assert "-a" in d and "+b" in d

    def test_diff_identique(self):
        assert calculer_diff("a\n", "a\n") == "aucun changement"
