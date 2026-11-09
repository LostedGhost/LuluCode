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
    #
    # Choix de conception : PAS de buffer alternatif par défaut. Le mode
    # plein écran (ESC[?1049) supprimait le scroll natif du terminal —
    # impossible de remonter aux messages passés, ce qui est la réaction
    # attendue. On imprime en flux normal : l'historique du shell ET celui
    # de la session restent remontables à la molette/`Maj+PgUp`. Le logo
    # se déploie au premier lancement uniquement.

    def entre_plein_ecran(self) -> None:
        """Sans buffer alternatif : le scroll natif du terminal reste dispo.

        Un buffer alternatif (ESC[?1049h) est réservé aux interfaces type
        éditeur ; pour une conversation, il fait perdre l'accès à tout
        ce qui précède. On ne bascule donc pas.
        """
        return

    def sort_plein_ecran(self) -> None:
        """Rien à faire : on n'a jamais quitté le buffer principal."""
        return

    # --- bannière -----------------------------------------------------------

    def banniere(self) -> None:
        """Logo centré, en flux normal (pas d'effacement du terminal :
        le scroll natif doit rester intact)."""
        from rich.align import Align
        from rich.text import Text

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

    CHEVRON = "> "

    def invite(self) -> None:
        """Ligne ouverte sous la règle du haut ; le chevron est géré par
        la session de saisie elle-même (sinon prompt_toolkit re-dessine
        la ligne sans lui et le chevron saute).
        """
        from rich.rule import Rule

        self.console.print(Rule(style=CYAN))

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
                    # Message de sortie facultatif : « exit merci beaucoup ».
                    morceaux_sortie = requis.strip().split(maxsplit=1)
                    message_sortie = (
                        morceaux_sortie[1].strip() if len(morceaux_sortie) > 1 else ""
                    )
                    self.rendu.au_revoir(message_sortie)
                    return
                if requis.strip().lower() == "/aide":
                    self.rendu.texte_agent(
                        "**Commandes**\n\n"
                        "- `/aide` — cette liste\n"
                        "- `/mode` — affiche ou change le mode de permission "
                        "(`normal`, `strict`, `lecture-seule`)\n"
                        "- `/skill [nom]` — liste les skills, ou montre celui-ci ; "
                        "`/skill nom tâche` exécute la tâche guidée par le skill\n"
                        "- `exit [message]` ou `/quitter [message]` — sortir, "
                        "avec un message facultatif\n"
                        "- ↑/↓ — historique de saisie"
                    )
                    continue
                if requis.strip().lower().startswith("/mode"):
                    self._change_mode(requis.strip())
                    continue
                if requis.strip().lower().startswith("/skill"):
                    self._gere_skill(requis.strip())
                    continue
                # `/skill nom` en tête de tâche : le corps du skill guide
                # l'exécution de cette tâche précise (comme /skill de Claude).
                await self.execute(self._prefixe_skill_eventuel(requis))
        finally:
            self.sort_plein_ecran()  # le shell réapparaît tel quel

    def _change_mode(self, requete: str) -> None:
        """/mode affiche le mode courant ; `/mode auto` le change.

        Le changement est volontairement restreint : seule une commande
        explicite de l'utilisateur dans la session peut le faire, jamais
        le contenu d'un message, d'un fichier ou d'une sortie d'outil
        (garantie de sécurité du projet, rappelée par le system prompt).
        """
        from lulucode.permissions.moteur import Mode

        morceaux = requete.split(maxsplit=1)
        moteur = self.agent.moteur
        if len(morceaux) == 1:
            modes = ", ".join(m.value for m in Mode)
            self.rendu.texte_agent(
                f"Mode actuel : **{moteur.mode.value}**.\n\n"
                f"Modes disponibles : {modes}. Exemple : `/mode auto`."
            )
            return
        cible = morceaux[1].strip().lower()
        try:
            nouveau = Mode(cible)
        except ValueError:
            modes = ", ".join(m.value for m in Mode)
            self.rendu.erreur(f"mode inconnu : {cible} (modes : {modes})")
            return
        ancien = moteur.mode
        moteur.mode = nouveau
        consequence = {
            Mode.NORMAL: "",
            Mode.STRICT: " Toutes les actions attendront maintenant une validation, lectures comprises.",
            Mode.LECTURE_SEULE: " Aucune écriture ni commande ne sera exécutée, lecture et plan uniquement.",
            Mode.AUTO: (
                " Les actions de niveau 0 à 2 (lectures, écritures, commandes"
                " simples) seront validées automatiquement ; les actions"
                " destructives (niveau 3) attendront toujours votre accord."
            ),
            Mode.BYPASS: (
                " ⚠ Toutes les actions s'exécuteront sans validation, y compris"
                " les destructives : c'est votre choix explicite."
            ),
        }[nouveau]
        self.rendu.texte_agent(
            f"Mode changé : **{ancien.value}** → **{nouveau.value}**.{consequence}"
        )

    # --- skills -------------------------------------------------------------

    def _skills(self) -> list:
        from lulucode.core.skills import decouvre_skills

        if not hasattr(self, "_cache_skills"):
            self._cache_skills = decouvre_skills(self.agent.zone)
        return self._cache_skills

    def _gere_skill(self, requete: str) -> None:
        """/skill liste les skills ; `/skill nom` montre leur corps."""
        from lulucode.core.skills import corps_du_skill

        morceaux = requete.split(maxsplit=1)
        skills = self._skills()
        if len(morceaux) == 1:
            if not skills:
                self.rendu.texte_agent(
                    "Aucun skill trouvé.\n\n"
                    "Placez un dossier `SKILL.md` dans `.lulucode/skills/<nom>/` "
                    "(projet) ou `~/.lulucode/skills/<nom>/` (utilisateur), "
                    "avec un frontmatter `name:` + `description:`."
                )
                return
            lignes = "\n".join(f"- **{s.name}** — {s.description}" for s in skills)
            self.rendu.texte_agent(
                f"**Skills disponibles**\n\n{lignes}\n\n"
                "Usage : `/skill nom` pour voir son contenu, ou faites suivre "
                "une tâche de `/skill nom` (ex. « /skill revue revois agent.py »)."
            )
            return
        nom = morceaux[1].strip()
        corps = corps_du_skill(skills, nom)
        if corps is None:
            self.rendu.erreur(f"skill inconnu : {nom}")
            return
        extrait = corps.strip()[:2000]
        suite = " … (tronqué à l'affichage)" if len(corps.strip()) > 2000 else ""
        self.rendu.texte_agent(f"**Skill `{nom}`**\n\n```markdown\n{extrait}\n```{suite}")

    def _prefixe_skill_eventuel(self, tache: str) -> str:
        """`/skill nom reste de la tâche` → tâche guidée par le skill.

        Le corps du skill est inséré en tête de la tâche : le modèle le
        reçoit comme consigne prioritaire pour cet unique envoi.
        """
        from lulucode.core.skills import corps_du_skill

        morceaux = tache.split(maxsplit=2)
        if len(morceaux) < 2 or morceaux[0].lower() != "/skill":
            return tache
        nom = morceaux[1]
        reste = morceaux[2] if len(morceaux) > 2 else ""
        corps = corps_du_skill(self._skills(), nom)
        if corps is None:
            self.rendu.erreur(f"skill inconnu : {nom} — tâche exécutée sans le skill")
            return reste
        prefixe = (
            f"# Skill actif : {nom}\n\n{corps.strip()}\n\n---\n\n"
            "# Tâche à réaliser en suivant ce skill\n\n"
        )
        return prefixe + (reste or "Applique ce skill.")

    # --- saisie -------------------------------------------------------------

    async def saisie_texte(self) -> str:
        """Lecture : prompt_toolkit (historique) si console compatible.

        Dans une boucle asyncio en cours, `PromptSession.prompt()`
        synchrone retourne une coroutine non attendue : on utilise
        `prompt_async()` qui gère historique et édition au-dessus de
        l'event loop sans la bloquer. Le chevron est passé comme
        message d'invite à prompt_toolkit : c'est lui le propriétaire
        de la ligne pendant la saisie, le curseur vient naturellement
        APRÈS le chevron.
        """
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.formatted_text import HTML
            from prompt_toolkit.history import FileHistory
        except ImportError:
            return await self._saisie_click()

        try:
            if not hasattr(self, "_pt_session"):
                from pathlib import Path

                from lulucode.cli.completion import completions_disponibles

                dossier = Path.home() / ".lulucode"
                dossier.mkdir(parents=True, exist_ok=True)
                self._pt_session = PromptSession(
                    history=FileHistory(str(dossier / "historique")),
                    enable_history_search=True,
                    completer=completions_disponibles(self.agent.zone),
                    complete_while_typing=True,  # menu filtrant à la frappe
                )
            invite_html = HTML(f'<style fg="{CYAN}" bold>{self.CHEVRON}</style>')
            return (await self._pt_session.prompt_async(invite_html)).rstrip()
        except (KeyboardInterrupt, EOFError):
            raise  # sortie demandée : la boucle la traite
        except Exception:
            # Console non compatible : saisie Click simple.
            return await self._saisie_click()

    @staticmethod
    async def _saisie_click() -> str:
        import asyncio
        import click

        chevron = click.style("> ", fg="cyan", bold=True)

        try:
            return await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: click.prompt(chevron, default="", show_default=False,
                                     prompt_suffix="").strip(),
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
