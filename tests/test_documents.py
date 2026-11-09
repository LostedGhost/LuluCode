"""Tests de l'outil lire_document : PDF/DOCX extraits, images vision."""

import base64
from pathlib import Path

import pytest

from lulucode.core.agent import Agent
from lulucode.tools.documents import (
    ResultatDocument,
    données_image_base64,
    lit_document,
    type_de_document,
)

pypdf = pytest.importorskip("pypdf", reason="extraction PDF requise pour les tests PDF")


@pytest.fixture()
def zone(tmp_path):
    return tmp_path


class TestTypage:
    def test_extension_pdf(self):
        assert type_de_document(Path("a.PDF")) == "pdf"

    def test_extension_docx(self):
        assert type_de_document(Path("r.docx")) == "docx"

    def test_extension_image(self):
        assert type_de_document(Path("p.png")) == "image"
        assert type_de_document(Path("photo.JPG")) == "image"

    def test_texte(self):
        assert type_de_document(Path("x.md")) == "texte"

    def test_inconnu(self):
        assert type_de_document(Path("binaire.xz")) == "inconnu"


class TestZoneEtPresence:
    def test_hors_zone_refuse(self, tmp_path):
        ailleurs = tmp_path.parent / "secret.pdf"
        r = lit_document(ailleurs, tmp_path)
        assert not r.ok and "hors de la zone" in r.erreur

    def test_inexistant(self, tmp_path):
        r = lit_document(tmp_path / "rien.pdf", tmp_path)
        assert not r.ok and "introuvable" in r.erreur

    def test_texte_passethrough(self, tmp_path):
        fichier = tmp_path / "note.md"
        fichier.write_text("hello", encoding="utf-8")
        r = lit_document(fichier, tmp_path)
        assert r.ok and "hello" in r.contenu


class TestPdf:
    def test_pdf_sans_texte_signale_scanné(self, tmp_path):
        """Un PDF vide/graphique renvoie le message scanné (pas un crash)."""
        from pypdf import PdfWriter

        chemin = tmp_path / "v.pdf"
        PdfWriter().write(str(chemin))
        r = lit_document(chemin, tmp_path)
        assert not r.ok
        assert "scanné" in r.erreur or "extractible" in r.erreur

    def test_pdf_corrompu_message_clair(self, tmp_path):
        chemin = tmp_path / "casse.pdf"
        chemin.write_bytes(b"%PDF-1.4\npas vraiment un pdf")
        r = lit_document(chemin, tmp_path)
        assert not r.ok and ("impossible" in r.erreur or "scanné" in r.erreur)


class TestImages:
    def test_image_sans_vision_erreur_explicite(self, tmp_path):
        image = tmp_path / "i.png"
        image.write_bytes(b"\x89PNG\r\n")
        r = lit_document(image, tmp_path, profil_vision=False)
        assert not r.ok
        assert "vision" in r.erreur.lower() and "profil" in r.erreur

    def test_base64_taille_et_mime(self, tmp_path):
        image = tmp_path / "p.png"
        image.write_bytes(b"contenu-image")
        donnees = données_image_base64(image)
        assert donnees is not None
        mime, code = donnees
        assert mime == "image/png"
        assert base64.b64decode(code) == b"contenu-image"

    def test_image_hors_zone_ne_rafle_pas(self, tmp_path):
        cible = tmp_path.parent / "sp.png"
        cible.write_bytes(b"x")
        r = lit_document(cible, tmp_path, profil_vision=True)
        assert not r.ok and "hors de la zone" in r.erreur


class TestVisionClient:
    def test_messages_avec_images_injecte_dans_le_dernier_user(self):
        from lulucode.model.client import _messages_avec_images

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": " regards ça"},
        ]
        images = [{"mime": "image/png", "base64": "AAAA"}]
        nouvelles = _messages_avec_images(messages, images)
        contenu = nouvelles[-1]["content"]
        assert isinstance(contenu, list)
        assert contenu[0]["type"] == "image_url"
        assert contenu[0]["image_url"]["url"].startswith("data:image/png;base64,")
        assert contenu[1] == {"type": "text", "text": " regards ça"}
        # Le message d'origine n'est pas muté.
        assert messages[1]["content"] == " regards ça"
