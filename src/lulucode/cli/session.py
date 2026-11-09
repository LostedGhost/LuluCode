"""Session interactive de LuluCode : bannière logo, saisie encadrée,
historique de saisie — affichage simple et fiable (pas de streaming).

L'affichage est séquentiel : la bannière au lancement, puis chaque
élément (saisie, action outil, réponse en Markdown, diff) s'imprime une
seule fois, comme dans un shell. Ajout LuluCodeFace Claude Code :
l'invite est entourée de deux règles cyan et la saisie garde un
historique persistant (flèches ↑/↓).
"""

from __future__ import annotations

from typing import Any

LOGO = """\
██╗      ██╗   ██╗ ██╗      ██╗   ██╗  ██████╗  ██████╗   ██████╗  ███████╗
██║      ██║   ██║ ██║      ██║   ██║ ██╔════╝ ██╔═══██╗ ██╔══██╗ ██╔════╝
██║      ██║   ██║ ██║      ██║   ██║ ██║      ██║   ██║ ██║  ██║ █████╗
██║      ██║   ██║ ██║      ██║   ██║ ██║      ██║   ██║ ██║  ██║ ██╔══╝
███████╗ ╚██████╔╝ ███████╗ ╚██████╔╝ ╚██████╗ ╚██████╔╝ ██████╔╝ ███████╗
╚══════╝  ╚═════╝ ╚══════╝  ╚═════╝  ╚═════╝  ╚═════╝  ╚═════╝  ╚══════╝
"""

CYAN = "#22d3ee"
TEXTE_BLANC = "#e6edf3"
GRIS = "#8b949e"


class Session:
    """Boucle interactive : plein écran réel, bannière, saisie encadrée.

    Plein écran réel : le terminal bascule sur son buffer alternatif
    (séquence OSC 1049) — l'historique du shell disparaît totalement
    pendant la session (impossible de remonter dessus au scroll) et
    revient intact à la sortie. C'est le mécanisme de Claude Code et
    des éditeurs plein terminal (vim, less).
    """

    def __init__(self, agent: Any, rendu: Any, *, version: str, profil: str, mode: str) -> None:
        self.agent = agent
        self.rendu = rendu
        self.version = version
        self.profil = profil
        self.mode = mode
        self.console = rendu.console

    # --- plein écran ---------------------------------------------------------

    def entre_plein_ecran(self) -> None:
        """Bascule le terminal sur le buffer alternatif (écran vierge)."""
        import sys as _sys

        if not self.console.is_terminal:
            return
        _sys.stdout.write("\x1b[?1049h\x1b[H")  # buffer alt + curseur en haut
        _sys.stdout.flush()

    def sort_plein_ecran(self) -> None:
        """Revient au buffer principal : l'historique du shell réapparaît."""
        import sys as _sys

        if not self.console.is_terminal:
            return
        _sys.stdout.write("\x1b[?1049l")
        _sys.stdout.flush()

    # --- bannière -----------------------------------------------------------

    def banniere(self) -> None:
        """Efface l'écran (mode plein écran) et affiche le logo centré."""
        from rich.align import Align
        from rich.text import Text

        # Mode plein écran : on efface ce qui précède (historique du
        # shell encore visible derrière, comme Claude Code au lancement).
        self.console.clear()
        self.console.print()
        self.console.print(Align.center(Text(LOGO.rstrip(), style=f"bold {CYAN}")))
        self.console.print(Align.center(Text(
            f"v{self.version} · profil {self.profil} · mode {self.mode}", style=GRIS
        )))
        self.console.print(Align.center(Text(
            "Un agent de code qui tourne chez vous.", style=TEXTE_BLANC
        )))
        self.console.print(Align.center(Text(
            "exit pour sortir · /aide pour l'aide · ↑/↓ historique", style=GRIS
        )))
        self.console.print()

    # --- invite -------------------------------------------------------------

    def invite(self) -> None:
        """L'invite entre deux règles cyan, avant chaque saisie."""
        from rich.rule import Rule
        from rich.text import Text

        self.console.print(Rule(style=CYAN))
        self.console.print(Text("> ", style=f"bold {CYAN}"), end="")
        # La règle du bas est tracée après la saisie (dans la boucle).
        self._saisie_en_cours = True

    def fin_invite(self) -> None:
        """Règle du bas après la lecture de la saisie."""
        from rich.rule import Rule

        self.console.print(Rule(style=CYAN))

    # --- exécution ----------------------------------------------------------

    async def execute(self, tache: str) -> None:
        """Exécute une tâche ; l'émetteur imprime les événements à la volée."""
        await self.agent.execute(
            tache,
            emetteur=_EmetteurSession(self.rendu),
            permission=_permission_session(self.rendu),
        )
        self.console.print()  # respiration après chaque tâche

    # --- boucle -------------------------------------------------------------

    async def boucle(self) -> None:
        from lulucode.cli.main import veut_sortir

        self.entre_plein_ecran()  # buffer alternatif : scrollback masqué
        try:
            self.banniere()
            while True:
                self.invite()
                try:
                    requis = await self.saisie_texte()
                finally:
                    self.fin_invite()
                if not requis:
                    continue
                if veut_sortir(requis):
                    self.rendu.au_revoir()
                    return
                if requis.strip().lower() == "/aide":
                    self.rendu.texte_agent(
                        "**Commandes**\n\n"
                        "- `/aide` — cette liste\n"
                        "- `exit` ou `/quitter` — sortir\n"
                        "- ↑/↓ — historique de saisie"
                    )
                    continue
                await self.execute(requis)
        finally:
            self.sort_plein_ecran()  # le shell réapparaît tel quel

    # --- saisie -------------------------------------------------------------

    async def saisie_texte(self) -> str:
        """Lecture : prompt_toolkit (historique) si console compatible.

        Dans une boucle asyncio en cours, `PromptSession.prompt()`
        synchrone retourne une coroutine non attendue : on utilise
        `prompt_async()` qui gère historique et édition au-dessus de
        l'event loop sans la bloquer.
        """
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
        except ImportError:
            return self._saisie_click()

        try:
            if not hasattr(self, "_pt_session"):
                from pathlib import Path

                dossier = Path.home() / ".lulucode"
                dossier.mkdir(parents=True, exist_ok=True)
                self._pt_session = PromptSession(
                    history=FileHistory(str(dossier / "historique")),
                    enable_history_search=True,
                )
            return (await self._pt_session.prompt_async("")).rstrip()
        except (KeyboardInterrupt, EOFError):
            raise  # sortie demandée : la boucle la traite
        except Exception:
            # Console non compatible : saisie Click simple.
            return await self._saisie_click()

    @staticmethod
    async def _saisie_click() -> str:
        import asyncio
        import click

        try:
            return await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: click.prompt("", default="", show_default=False).strip(),
            )
        except (KeyboardInterrupt, EOFError):
            raise


class _EmetteurSession:
    """Imprime chaque événement du cœur une seule fois, dans l'ordre."""

    def __init__(self, rendu: Any) -> None:
        self.rendu = rendu

    def emettre(self, evenement: Any) -> None:
        from lulucode.core.events import Kind

        if evenement.type is Kind.TEXTE:
            if not evenement.donnees.get("deja_affiche"):
                self.rendu.texte_agent(evenement.donnees.get("texte", ""))
        elif evenement.type is Kind.OUTIL_APPEL:
            args = evenement.donnees.get("arguments", {})
            cible = (args.get("chemin") or args.get("commande")
                     or args.get("motif")
                     or ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items()))
            self.rendu.outil(evenement.donnees.get("outil", ""), str(cible))
        elif evenement.type is Kind.DIFF:
            self.rendu.diff(
                evenement.donnees.get("chemin", ""), evenement.donnees.get("diff", "")
            )
        elif evenement.type is Kind.PLAFOND:
            self.rendu.plafond(str(evenement.donnees.get("raison", "")))
        elif evenement.type is Kind.ERREUR:
            self.rendu.erreur(str(evenement.donnees.get("message", "")))


def _permission_session(rendu: Any):
    async def _demande(demande: dict) -> bool:
        choix = rendu.permission(demande)
        return choix in ("o", "s")

    return _demande
