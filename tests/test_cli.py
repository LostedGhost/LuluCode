"""Tests du CLI (Click + CliRunner, sans réseau ni modèle réel)."""

from click.testing import CliRunner

from lulucode.cli.main import app


def test_aide_principale():
    resultat = CliRunner().invoke(app, ["--help"])
    assert resultat.exit_code == 0
    assert "run" in resultat.output
    assert "config" in resultat.output


def test_version():
    resultat = CliRunner().invoke(app, ["--version"])
    assert resultat.exit_code == 0
    assert "0.1.0" in resultat.output


def test_config_init_cree_le_fichier(tmp_path, monkeypatch):
    monkeypatch.setenv("LULUCODE_CONFIG", str(tmp_path / "config.toml"))
    resultat = CliRunner().invoke(app, ["config", "init"])
    assert resultat.exit_code == 0, resultat.output
    assert "Configuration créée" in resultat.output
    assert (tmp_path / "config.toml").is_file()

    # Deuxième appel : refusé, la config existe déjà.
    resultat2 = CliRunner().invoke(app, ["config", "init"])
    assert resultat2.exit_code == 1


def test_run_demande_configuration_absente(tmp_path, monkeypatch):
    monkeypatch.setenv("LULUCODE_CONFIG", str(tmp_path / "inexistante.toml"))
    resultat = CliRunner().invoke(app, ["run", "-t", "bonjour"])
    assert resultat.exit_code == 1
    assert "config" in resultat.output.lower() or "introuvable" in resultat.output
