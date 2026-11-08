"""Session plein écran de LuluCode, à la façon des agents modernes.

L'écran est un journal défilant (bannière, historique des échanges,
actions d'outils) ; l'invite reste fixée en bas, entre deux lignes
tracées, avec historique de saisie (flèches haut/bas comme en shell).
Les réponses du modèle arrivent en streaming, texte au fil de l'eau.

Principe : Rich Live re-rend le Group (journal + panneau de saisie) à
chaque changement ; le terminal garde l'écran, seul le contenu bouge.
Sans prompt_toolkit, repli sur la saisie Click (pas d'historique).
"""

from __future__ import annotations

import asyncio
from typing import Any

LOGO = """\
 ██╗     ██╗   ██╗██╗     ██╗   ██╗ ██████╗ ██████╗ ██████╗ ███████╗
 ██║     ██║   ██║██║     ██║   ██║██╔════╝██╔═══██╗██╔══██╗██╔════╝
 ██║     ██║   ██║██║     ██║   ██║██║     ██║   ██║██████╔╝█████╗
 ██║     ██║   ██║██║     ██║   ██║██║     ██║   ██║██╔══██╗██╔══╝
 ███████╗╚██████╔╝██║     ╚██████╔╝╚██████╗╚██████╔╝██║  ██║███████╗
 ╚══════╝ ╚═════╝ ╚═╝      ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
"""

CYAN = "#22d3ee"
TEXTE_BLANC = "#e6edf3"
GRIS = "#8b949e"


class Session:
    """Boucle interactive plein écran : journal + saisie fixée en bas."""

    def __init__(self, agent: Any, rendu: Any, *, version: str, profil: str, mode: str) -> None:
        self.agent = agent
        self.rendu = rendu
        self.version = version
        self.profil = profil
        self.mode = mode
        self.blocs: list[Any] = []       # journal : blocs déjà figés
        self.courant: Any = None         # bloc en cours (streaming)
        self.tampon_stream = ""          # fragments de streaming accumulés
        self.suggestion = ""             # last saisie en attente d'Enter

    # --- composition d'écran ------------------------------------------------

    def ecran(self, saisie: str = "") -> Any:
        """Compose l'écran : bannière ou journal, puis panneau de saisie."""
        from rich.console import Group
        from rich.rule import Rule
        from rich.text import Text

        blocs: list[Any] = []
        if not self.blocs and self.courant is None:
            from rich.align import Align
            from rich.panel import Panel

            corps = Text()
            corps.append("Un agent de code qui tourne chez vous.\n", style=TEXTE_BLANC)
            corps.append("exit", style=f"bold {CYAN}")
            corps.append(" pour sortir   ", style=GRIS)
            corps.append("/aide", style=f"bold {CYAN}")
            corps.append(" pour l'aide", style=GRIS)
            logo = Text(LOGO.rstrip(), style=f"bold {CYAN}")
            sous_titre = Text(
                f"v{self.version} · profil {self.profil} · mode {self.mode}",
                style=GRIS,
            )
            blocs = [
                Align.center(logo),
                Align.center(sous_titre),
                Align.center(corps),
            ]
        else:
            blocs = list(self.blocs)
            if self.courant is not None:
                blocs.append(self.courant)

        # Panneau de saisie, toujours en bas : deux règles cyan entre
        # lesquelles l'invite et la saisie en cours.
        zone = Text()
        zone.append("> ", style=f"bold {CYAN}")
        zone.append(saisie or "…", style=TEXTE_BLANC)
        return Group(*blocs, Text(""), Rule(style=CYAN), zone, Rule(style=CYAN))

    # --- journal -----------------------------------------------------------

    def fige_courant(self) -> None:
        """Fige le bloc courant dans le journal et le vide."""
        if self.courant is not None:
            self.blocs.append(self.courant)
            self.courant = None
            self.tampon_stream = ""

    def ajoute_bloc(self, bloc: Any) -> None:
        """Ajoute un bloc figé au journal (action outil, diff, erreur...)."""
        self.figes_avant()
        self.blocs.append(bloc)

    def figes_avant(self) -> None:
        self.fige_courant()

    # --- exécution -----------------------------------------------------------

    async def execute(self, tache: str) -> None:
        """Exécute une tâche en remplissant le journal en continu."""
        from rich.live import Live

        self.ajoute_bloc(self.rendu.bloc_utilisateur(tache))

        with Live(
            self.ecran(),
            console=self.rendu.console,
            refresh_per_second=12,
            screen=False,
            vertical_overflow="visible",
        ) as live:
            ecrivain = _EcrivainStream(self, live)
            await self.agent.execute(
                tache,
                emetteur=_EmetteurSession(self),
                permission=_permission_session(self.rendu),
                sur_ecriture=ecrivain.fragment,
            )
        self.figes_avant()

    # --- boucle ------------------------------------------------------------
    async def boucle(self) -> None:
        from lulucode.cli.main import veut_sortir

        while True:
            requis = self.saisie()
            if not requis:
                continue
            if veut_sortir(requis):
                self.rendu.au_revoir()
                return
            if requis.strip().lower() == "/aide":
                self.ajoute_bloc(self.rendu.bloc_utilisateur("/aide"))
                self.ajoute_bloc(self.rendu.blob_texte(
                    "**Commandes**\n\n"
                    "- `/aide` — cette liste\n"
                    "- `exit` ou `/quitter` — sortir\n"
                    "- ↑/↓ — historique de saisie"
                ))
                self.figes_avant()
                self.affiche_fige()
                continue
            await self.execute(requis)

    def affiche_fige(self) -> None:
        """Re-rend l'écran une fois hors Live (commandes locales)."""
        from rich.console import Console
        self.rendu.console.print(self.ecran(self.suggestion))

    def saisie(self) -> str:
        """Lecture de saisie : prompt_toolkit si dispo, sinon Click.

        prompt_toolkit exige une vraie console (Win32 sous Windows) :
        sans elle, repli propre sur la saisie Click simple.
        KeyboardInterrupt / EOFError remontent à la boucle (sortie).
        """
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
        except ImportError:
            return self._saisie_click()

        try:
            if not hasattr(self, "_pt_session"):
                from pathlib import Path

                hist_dir = Path.home() / ".lulucode"
                hist_dir.mkdir(parents=True, exist_ok=True)
                self._pt_session = PromptSession(
                    history=FileHistory(str(hist_dir / "historique")),
                    enable_history_search=True,
                )
            return self._pt_session.prompt("> ").strip()
        except (KeyboardInterrupt, EOFError):
            raise  # sortie demandée : la boucle la traite
        except Exception:
            # Console non compatible (pipe, tmux exotique, Cygwin...) :
            # repli propre sans planter la session.
            return self._saisie_click()

    @staticmethod
    def _saisie_click() -> str:
        import click

        try:
            return click.prompt(click.style("> ", fg="cyan", bold=True), default="",
                                show_default=False).strip()
        except (KeyboardInterrupt, EOFError):
            raise


class _EcrivainStream:
    """Accumule les fragments du modèle et met à jour le bloc courant."""

    def __init__(self, session: Session, live: Any) -> None:
        self.session = session
        self.live = live

    def fragment(self, fragment: str) -> None:
        self.session.figes_avant()
        self.session.tampon_stream += fragment
        self.session.courant = self.session.rendu.blob_texte(self.session.tampon_stream)
        self.live.update(self.session.ecran())


class _EmetteurSession:
    """Traduit les événements du cœur en blocs du journal plein écran."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def emettre(self, evenement: Any) -> None:
        from lulucode.core.events import Kind

        r = self.session.rendu
        if evenement.type is Kind.TEXTE:
            # Streaming : le fragment a déjà été affiché au fil de l'eau.
            # Mode non-streamé : le bloc va au journal direct.
            if not evenement.donnees.get("deja_affiche"):
                self.session.figes_avant()
                self.session.ajoute_bloc(r.blob_texte(evenement.donnees.get("texte", "")))
        elif evenement.type is Kind.OUTIL_APPEL:
            args = evenement.donnees.get("arguments", {})
            cible = (args.get("chemin") or args.get("commande")
                     or args.get("motif") or ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items()))
            self.session.ajoute_bloc(r.outil_bloque(evenement.donnees.get("outil", ""), str(cible)))
        elif evenement.type is Kind.DIFF:
            self.session.ajoute_bloc(r.diff_bloque(
                evenement.donnees.get("chemin", ""), evenement.donnees.get("diff", "")
            ))
        elif evenement.type is Kind.PLAFOND:
            self.session.ajoute_bloc(r.plafond_bloque(str(evenement.donnees.get("raison", ""))))
        elif evenement.type is Kind.ERREUR:
            self.session.ajoute_bloc(r.erreur_bloque(str(evenement.donnees.get("message", ""))))


def _permission_session(rendu: Any):
    async def _demande(demande: dict) -> bool:
        # La permission doit se faire dans Live : elle s'affiche dans la
        # console Rich du rendu, ce qui force la sortie propre du Live.
        choix = rendu.permission(demande)
        return choix in ("o", "s")

    return _demande
