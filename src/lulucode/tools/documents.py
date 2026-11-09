"""Lecture de documents non-texte : PDF, Word, images (vision).

Stratégie par type :
- PDF texte    : pypdf si installé, sinon message d'installation explicite.
- PDF scanné   : sans couche OCR locale, on tente la vision si le profil
                du modèle en a une ; sinon message clair (DocScan à venir).
- DOCX         : python-docx si installé, sinon message d'installation.
- Image        : vision par le modèle (base64 au format OpenAI) si
                `vision = true` dans le profil ; sinon erreur avec conseils.

Aucune dépendance n'est obligatoire : chaque extracteur absent produit
une erreur explicite au lieu de faire planter l'agent.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

_EXTENSIONS_PDF = {".pdf"}
_EXTENSIONS_DOCX = {".docx"}
_EXTENSIONS_IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
_EXTENSIONS_TEXTE = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".toml", ".yaml", ".yml",
    ".html", ".css", ".sh", ".rs", ".go", ".java", ".c", ".cpp", ".h",
    ".csv", ".ini", ".toml", ".rst", ".xml", ".svg",
}


@dataclass(slots=True)
class ResultatDocument:
    """Contenu extrait d'un document, ou erreur explicite."""

    ok: bool
    contenu: str
    erreur: str = ""


def type_de_document(chemin: Path) -> str:
    """pdf | docx | image | texte | inconnu, selon l'extension."""
    suffixe = chemin.suffix.lower()
    if suffixe in _EXTENSIONS_PDF:
        return "pdf"
    if suffixe in _EXTENSIONS_DOCX:
        return "docx"
    if suffixe in _EXTENSIONS_IMAGE:
        return "image"
    if suffixe in _EXTENSIONS_TEXTE:
        return "texte"
    return "inconnu"


def lire_pdf(chemin: Path, limite_pages: int = 60) -> ResultatDocument:
    """Extraction du texte d'un PDF via pypdf (installable)."""
    try:
        from pypdf import PdfReader  # installé via `pip install lulucode[documents]`
    except ImportError:
        return ResultatDocument(
            False, "",
            "la lecture de PDF exige le paquet pypdf : "
            "« python -m pipx inject lulucode pypdf » (ou pip install pypdf)",
        )
    try:
        lecteur = PdfReader(str(chemin))
        pages = []
        for page in lecteur.pages[:limite_pages]:
            texte = (page.extract_text() or "").strip()
            if texte:
                pages.append(texte)
        if not pages:
            return ResultatDocument(
                False, "",
                "aucun texte extractible : le PDF est probablement scanné "
                "(lecture visuelle indisponible pour ce modèle — voir "
                "profil.vision ou DocScan)",
            )
        texte_complet = "\n\n".join(pages)
        if len(texte_complet) > 150_000:
            texte_complet = texte_complet[:150_000] + "\n… (document tronqué)"
        return ResultatDocument(True, texte_complet)
    except Exception as e:  # PDF corrompu, protégé, format exotique
        return ResultatDocument(False, "", f"lecture impossible : {e}")


def lire_docx(chemin: Path, limite_paragraphes: int = 2000) -> ResultatDocument:
    """Extraction du texte d'un .docx via python-docx (installable)."""
    try:
        import docx  # python-docx
    except ImportError:
        return ResultatDocument(
            False, "",
            "la lecture de .docx exige python-docx : "
            "pip install python-docx (ou pipx inject lulucode python-docx)",
        )
    try:
        document = docx.Document(str(chemin))
        lignes = []
        for paragraphe in document.paragraphs[:limite_paragraphes]:
            if p := paragraphe.text.strip():
                lignes.append(p)
        for table in document.tables[:50]:
            for rangée in table.rows[:100]:
                cellules = [c.text.strip() for c in rangée.cells]
                lignes.append(" | ".join(cellules))
        if not lignes:
            return ResultatDocument(True, "(document vide)")
        return ResultatDocument(True, "\n".join(lignes)[:150_000])
    except Exception as e:
        return ResultatDocument(False, "", f"lecture impossible : {e}")


def ocr_tesseract(chemin: Path, langue: str = "fra+eng") -> ResultatDocument:
    """OCR local via Tesseract, s'il est installé sur la machine.

    Priorité pour les images : extrait le texte (captures, scans, photos
    de documents) sans consommer le modèle ; la description d'ensemble
    d'une image reste le domaine de la vision.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ResultatDocument(
            False, "",
            "OCR local indisponible : pip install pytesseract pillow, "
            "et le binaire Tesseract (https://github.com/UB-Mannheim/tesseract/wiki)",
        )
    try:
        texte = pytesseract.image_to_string(Image.open(str(chemin)), lang=langue)
    except pytesseract.TesseractNotFoundError:
        return ResultatDocument(
            False, "",
            "le binaire Tesseract n'est pas installé ou pas dans le PATH : "
            "https://github.com/UB-Mannheim/tesseract/wiki (WINDOWS : cocher "
            "les langues French + English à l'installation)",
        )
    except Exception as e:
        return ResultatDocument(False, "", f"OCR impossible : {e}")
    texte = texte.strip()
    if not texte:
        return ResultatDocument(False, "aucun texte détecté par l'OCR — "
                                "l'image ne contient probablement pas de texte "
                                "(utilisez la vision pour une description)")
    return ResultatDocument(True, texte)


def données_image_base64(chemin: Path) -> tuple[str, str] | None:
    """(mimeType, base64) pour envoyer l'image au modèle vision."""
    try:
        brut = chemin.read_bytes()
    except OSError:
        return None
    extension = chemin.suffix.lower().lstrip(".")
    mime = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "webp": "image/webp", "gif": "image/gif",
    }.get(extension, "image/png")
    return mime, base64.b64encode(brut).decode("ascii")


def lit_document(
    chemin: Path,
    zone: Path,
    *,
    profil_vision: bool = False,
    question: str = "",
) -> ResultatDocument:
    """Point d'entrée de l'outil : route par type de document.

    Tout chemin hors zone est refusé (même garde que lire_fichier).
    """
    from lulucode.tools.fichiers import verifier_zone

    if err := verifier_zone(chemin, zone):
        return ResultatDocument(False, "", err)
    if not chemin.is_file():
        return ResultatDocument(False, "", f"fichier introuvable : {chemin}")

    genre = type_de_document(chemin)
    if genre == "texte":
        from lulucode.tools.fichiers import lire_fichier

        r = lire_fichier(chemin, zone)
        return ResultatDocument(r.ok, r.contenu, r.erreur)
    if genre == "pdf":
        return lire_pdf(chemin)
    if genre == "docx":
        return lire_docx(chemin)
    if genre == "image":
        # Vision d'abord (le LLM décrit ET lit le texte) ; l'OCR local
        # n'est qu'un recours si le profil n'a pas de vision.
        if profil_vision:
            return ResultatDocument(True, "")  # la façade enverra l'image au modèle
        ocr = ocr_tesseract(chemin)
        if ocr.ok:
            return ResultatDocument(True, "[texte extrait par OCR local]\n" + ocr.contenu)
        return ResultatDocument(
            False, "",
            "lecture d'image impossible dans cette session :\n"
            "- vision de modèle : profil sans `vision = true` "
            "(le serveur doit router vers un modèle vision)\n"
            f"- OCR local : {ocr.erreur}",
        )
    return ResultatDocument(
        False, "",
        f"type de fichier non pris en charge : {chemin.suffix!r} "
        "(PRIS EN CHARGE : pdf, docx, images ; texte via lire_fichier)",
    )
