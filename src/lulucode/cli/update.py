"""Mise à jour de lulucode installé via pipx.

Aujourd'hui le paquet vient d'un dossier local (pas encore de PyPI) :
`lulucode update` tire le dépôt puis réinstalle via pipx. Quand le paquet
sera publié sur PyPI, la même commande passera par `pipx upgrade`.

La source réelle de vérité est `direct_url.json` des métadonnées
d'installation : il distingue PyPI, dossier local et édition (editable).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import unquote, urlparse


@dataclass(slots=True)
class Installation:
    """Comment lulucode est installé sur cette machine."""

    mode: str  # "pypi" | "local" | "editable" | "inconnu"
    source: str | None  # chemin du dépôt local, URL distante, ou None


def detecte_installation(nom_paquet: str = "lulucode") -> Installation:
    """Lit les métadonnées du paquet pour savoir comment il est installé."""
    try:
        dist = distribution(nom_paquet)
    except Exception:
        return Installation("inconnu", None)

    brut = dist.read_text("direct_url.json")
    if not brut:
        # Sans direct_url, l'installation vient de PyPI en général.
        return Installation("pypi", None)
    try:
        donnees = json.loads(brut)
    except ValueError:
        return Installation("inconnu", None)

    if donnees.get("dir_info", {}).get("editable"):
        return Installation("editable", chemin_depuis_url(donnees.get("url", "")))
    url = donnees.get("url", "")
    if url.startswith("file:"):
        return Installation("local", chemin_depuis_url(url))
    if url:
        return Installation("pypi", url)
    return Installation("inconnu", None)


def chemin_depuis_url(url: str) -> str | None:
    """Convertit une URL file:/// en chemin système valide.

    `file:///C:/projets` donne `/C:/projets` (forme POSIX) ; sous Windows
    on retire la barre oblique initiale pour obtenir `C:/projets`.
    """
    if not url:
        return None
    chemin = unquote(urlparse(url).path)
    if not chemin:
        return None
    if chemin.startswith("/") and chemin[2:3] == ":":
        chemin = chemin[1:]
    return chemin


def version_actuelle(nom_paquet: str = "lulucode") -> str:
    try:
        return distribution(nom_paquet).version
    except Exception:
        return "inconnue"


def commande_pipx() -> list[str]:
    """Commande pipx disponible : binaire sur le PATH, sinon module python.

    Exception : si on tourne depuis le venv pipx de lulucode (lancement
    par l'exe), `sys.executable` pointe dans un environnement que pipx
    doit remplacer — verrouillé sous Windows pendant l'exécution. On
    cherche alors un python hors venv (launcher `py`, puis `python` du
    PATH), pour que la réinstallation puisse désinstaller proprement.
    """
    pipx = shutil.which("pipx")
    if pipx:
        return [pipx]
    marque = ("pipx", "venvs")
    python = sys.executable
    parents = Path(python).resolve().parents
    dans_venv_pipx = any(
        p.name == "venvs" and p.parent.name == "pipx" for p in parents
    )
    if dans_venv_pipx:
        for candidat in ("py", "python3", "python"):
            trouve = shutil.which(candidat)
            if trouve and not any(
                p.name == "venvs" and p.parent.name == "pipx"
                for p in Path(trouve).resolve().parents
            ):
                python = trouve
                break
    return [python, "-m", "pipx"]


def tags_git(chemin_repo: str | None) -> list[str]:
    """Liste les tags du dépôt local, sans réseau."""
    if not chemin_repo or not Path(chemin_repo).is_dir():
        return []
    try:
        out = subprocess.run(
            ["git", "-C", chemin_repo, "tag", "-l"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return sorted(l for l in out.stdout.splitlines() if l.strip())


def url_origine_git(chemin_repo: str | None) -> str | None:
    """URL du remote origin du dépôt local, en https/ssh:// utilisable par pip."""
    if not chemin_repo or not Path(chemin_repo).is_dir():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", chemin_repo, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    url = out.stdout.strip()
    if not url or url.startswith(("http", "ssh://")):
        return url or None
    if url.startswith("git@"):
        # git@github.com:owner/repo.git -> ssh://git@github.com/owner/repo.git
        partie_serveur, _, partie_chemin = url.partition(":")
        return f"ssh://{partie_serveur}/{partie_chemin.lstrip('/')}"
    return None


def versions_pypi(nom_paquet: str = "lulucode", delai_s: int = 15) -> list[str]:
    """Liste les versions publiées sur PyPI (réseau sortant)."""
    import urllib.request

    with urllib.request.urlopen(
        f"https://pypi.org/pypi/{nom_paquet}/json", timeout=delai_s
    ) as reponse:
        donnees = json.load(reponse)
    return sorted(donnees.get("releases", {}), key=_version_cle)


def _version_cle(v: str) -> tuple[int, ...]:
    """Clé de tri tolérante : 0.2.1 -> (0, 2, 1) ; incompréhensible -> (0,)."""
    morceaux: list[int] = []
    for morceau in v.replace("-", ".").split("."):
        try:
            morceaux.append(int(morceau))
        except ValueError:
            morceaux.append(0)
    return tuple(morceaux)


def liste_versions(installation: Installation | None = None) -> list[str]:
    """Versions disponibles selon le mode d'installation (jamais d'exception)."""
    installation = installation or detecte_installation()
    if installation.mode in ("local", "editable"):
        return tags_git(installation.source)
    if installation.mode == "pypi":
        try:
            return versions_pypi()
        except (OSError, ValueError):
            return []
    return []


def git_pull(chemin_repo: str, journal: list[str]) -> int:
    """Met le dépôt local à jour en fast-forward uniquement (sans écraser)."""
    try:
        out = subprocess.run(
            ["git", "-C", chemin_repo, "pull", "--ff-only"],
            capture_output=True, text=True, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        journal.append(f"git pull impossible : {e}")
        return 1
    if out.returncode != 0:
        journal.append(f"git pull échoué : {(out.stderr or out.stdout).strip()}")
        return 1
    journal.append((out.stdout or "dépôt déjà à jour").strip())
    return 0


def _lance(cmd: list[str], journal: list[str], delai_s: int = 300) -> int:
    """Exécute une commande externe et note son résultat dans le journal."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=delai_s)
    except (OSError, subprocess.TimeoutExpired) as e:
        journal.append(f"commande impossible ({' '.join(cmd[:2])}…) : {e}")
        return 1
    texte = (out.stdout or "").strip()
    if texte:
        journal.append(texte)
    if out.returncode != 0:
        journal.append(f"échec (code {out.returncode}) : {(out.stderr or '').strip()}")
    return out.returncode


def mets_a_jour(version: str | None = None, installation: Installation | None = None) -> tuple[int, list[str]]:
    """Met lulucode à jour. Renvoie (code de sortie, lignes de journal).

    - mode local/éditable : git pull (fast-forward) puis pipx réinstalle ;
      avec `version`, installe le tag demandé via le remote git, sans
      modifier le dépôt local.
    - mode PyPI : pipx upgrade ; avec `version`, inst lulucode==version.

    Cas particulier Windows : si lulucode tourne depuis le venv pipx
    qu'il faut remplacer, la réinstallation est différée — Windows
    verrouille lulucode.exe pendant qu'il s'exécute. On écrit un petit
    script batch qui attend la fin du processus puis relance pipx, et
    on le délègue au planificateur via `start /b` ; le message final
    invite l'utilisateur à patienter quelques secondes.
    """
    journal: list[str] = []
    installation = installation or detecte_installation()
    journal.append(
        "installation détectée : "
        + installation.mode
        + (f" — {installation.source}" if installation.source else "")
    )
    if installation.mode == "inconnu":
        journal.append("impossible de localiser l'installation de lulucode")
        return 1, journal

    if installation.mode in ("local", "editable"):
        repo = installation.source
        if version:
            url_git = url_origine_git(repo)
            if not url_git:
                journal.append(
                    "installer une version précise exige un remote 'origin' git"
                )
                return 1, journal
            spec = f"lulucode @ git+{url_git}@{version}"
            code = _lance(commande_pipx() + ["install", "--force", spec], journal)
        else:
            code = git_pull(repo, journal)
            if code == 0:
                code = _reinstalle_si_possible(
                    commande_pipx() + ["install", "--force", repo], journal
                )
    else:
        cmds = commande_pipx()
        if version:
            cmds += ["install", "--force", f"lulucode=={version}"]
        else:
            cmds += ["upgrade", "lulucode"]
        code = _reinstalle_si_possible(cmds, journal)

    if code == 0:
        journal.append(f"lulucode est à jour — version {version_actuelle()}")
    return code, journal


def _dans_venv_pipx_actif() -> bool:
    """True si lulucode.exe lui-même tourne depuis le venv pipx."""
    executable = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path(sys.executable)
    return any(
        p.name == "venvs" and p.parent.name == "pipx" for p in executable.parents
    )


def _reinstalle_si_possible(cmd: list[str], journal: list[str]) -> int:
    """Réinstalle via pipx, en différant si l'exe courant verrouille le venv.

    Windows refuse de remplacer lulucode.exe pendant qu'il s'exécute deux
    fois sur deux : la sortie de lulucode update laisse quelques secondes,
    puis un script temporaire relance pipx.
    """
    if os.name != "nt" or not _dans_venv_pipx_actif():
        return _lance(cmd, journal)

    # Différé : le batch attend que lulucode update se termine.
    import tempfile

    ligne_cmd = subprocess.list2cmdline(cmd)
    python_sys = _python_systeme_pour_pipx()
    script = (
        "@echo off\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f"{subprocess.list2cmdline([python_sys])} -m pipx install --force "
        f"{_spec_depuis_ligne(ligne_cmd)}\r\n"
    )
    try:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".bat", delete=False, prefix="lulucode-update-"
        )
        handle.write(script)
        handle.close()
    except OSError as e:
        journal.append(f"impossible d'écrire le script de mise à jour : {e}")
        return 1
    try:
        subprocess.Popen(
            ["cmd", "/c", handle.name],
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        journal.append(f"lancement du script différé impossible : {e}")
        return 1
    journal.append(
        f"réinstallation lancée en arrière-plan ({handle.name}) ; "
        "lulucode sera mis à jour dans quelques secondes après cette commande"
    )
    return 0


def _python_systeme_pour_pipx() -> str:
    """Python hors venv pipx pour relancer pipx dans le script différé."""
    for candidat in ("py", "python3", "python"):
        trouve = shutil.which(candidat)
        if trouve and not any(
            p.name == "venvs" and p.parent.name == "pipx"
            for p in Path(trouve).resolve().parents
        ):
            return trouve
    return sys.executable


def _spec_depuis_ligne(ligne: str) -> str:
    """Extrait le spec d'installation après `pipx install --force `."""
    marqueur = "--force"
    pos = ligne.find(marqueur)
    if pos == -1:
        return ""
    return ligne[pos + len(marqueur):].strip()
