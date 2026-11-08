"""Rendu terminal de LuluCode, à l'image des visuels du README (assets/).

Palette et gabarits des SVG : fond #0d1117, panneaux #161b22/bordure
#30363d, accents cyan #22d3ee et violet #a78bfa, statuts
vert/bleu/jaune/rouge. L'affichage des réponses suit le style des
agents de code modernes : Markdown rendu (titres, listes, gras, blocs
de code colorés), glyphes ⏺ pour les actions outil, encadrés pour les
diff et les demandes de permission.

Riche, sans dépendance obligatoire : sans Rich installé, la façade
retombe sur un affichage sobre en monochrome.
"""

from __future__ import annotations

from typing import Any

# --- Palette de la bible (assets/*.svg, studio/bible.md) -------------------
FOND = "#0d1117"
PANNEAU = "#161b22"
BORDE = "#30363d"
TEXTE = "#e6edf3"
SECONDAIRE = "#8b949e"
CYAN = "#22d3ee"
VIOLET = "#a78bfa"
VERT = "#3fb950"
BLEU = "#58a6ff"
JAUNE = "#d29922"
ROUGE = "#f85149"

# Libellé court de chaque outil, comme les étiquettes [lecture] des SVG.
_ETIQUETTES = {
    "lire_fichier": "lecture",
    "lister_dossier": "lecture",
    "chercher_code": "recherche",
    "ecrire_fichier": "écriture",
    "lancer_commande": "commande",
}

GLYPHE = "⏺"


class RenduSimple:
    """Rendu de secours sans Rich : monochrome, même contenu."""

    def __init__(self) -> None:
        import click

        self._click = click

    def banniere(self, version: str, profil: str, mode: str) -> None:
        self._click.echo("")
        self._click.echo("LuluCode — agent de code local. `exit` pour sortir, `/aide` pour l'aide.")
        self._click.echo("")

    def etat(self, version: str, profil: str, mode: str, dossier: str) -> None:
        self._click.echo(
            f"LuluCode {version}  |  profil {profil}  |  mode {mode}  |  dossier {dossier}"
        )

    def invite(self) -> str:
        return "> "

    def texte_agent(self, texte: str) -> None:
        self._click.echo(texte)

    def curseur(self, actif: bool) -> None:
        """Change la forme du curseur du terminal (sans effet sans Rich)."""
        pass

    def outil(self, nom: str, cible: str) -> None:
        etiquette = _ETIQUETTES.get(nom, "outil")
        suffixe = f" {cible}" if cible else ""
        self._click.echo(f"  [lecture] {etiquette}{suffixe}")

    def diff(self, chemin: str, texte_diff: str) -> None:
        self._click.echo(f"  [diff] {chemin}")
        for ligne in texte_diff.splitlines():
            self._click.echo(f"  {'+' if ligne.startswith('+') else ' '}{ligne}")

    def erreur(self, message: str) -> None:
        self._click.echo(f"  [erreur] {message}", err=True)

    def permission(self, demande: dict[str, Any]) -> str:
        self._click.echo(f"  [permission] {demande['outil']} — {demande['raison']}")
        return self._click.prompt(
            "  [o] une fois  [s] pour la session  [n] refuser",
            type=click.Choice(["o", "s", "n"]),
            default="n",
            show_default=False,
        )

    def plafond(self, raison: str) -> None:
        self._click.echo(f"  [plafond] {raison}")

    def au_revoir(self) -> None:
        self._click.echo("À bientôt.")


class RenduRiche:
    """Rendu Rich fidèle aux SVG du README, réponses en Markdown."""

    def __init__(self) -> None:
        from rich.console import Console
        from rich.theme import Theme

        self.console = Console(
            highlight=False,
            theme=Theme({
                "texte": TEXTE,
                "gris": SECONDAIRE,
                "cyan": CYAN,
                "violet": VIOLET,
                "vert": VERT,
                "bleu": BLEU,
                "jaune": JAUNE,
                "rouge": ROUGE,
                "etat": SECONDAIRE,
            }),
        )

    # --- accueil -----------------------------------------------------------

    def banniere(self, version: str, profil: str, mode: str) -> None:
        """Encadré d'accueil, façon agents de code : identité + astuces."""
        from rich.panel import Panel
        from rich.text import Text

        corps = Text()
        corps.append("LuluCode", style=f"bold {CYAN}")
        corps.append(f" {version}\n", style=SECONDAIRE)
        corps.append("Un agent de code qui tourne chez vous.\n\n", style=TEXTE)
        corps.append("exit", style=f"bold {CYAN}")
        corps.append(" pour sortir   ", style=SECONDAIRE)
        corps.append("/aide", style=f"bold {CYAN}")
        corps.append(" pour l'aide", style=SECONDAIRE)
        self.console.print()
        self.console.print(
            Panel(
                corps,
                border_style=CYAN,
                style=f"on {FOND}",
                padding=(0, 2),
            )
        )
        self.console.print()

    def etat(self, version: str, profil: str, mode: str, dossier: str) -> None:
        from rich.text import Text

        # Toute la ligne d'état en gris clair ; le contenu utile
        # (réponses de l'agent) est en blanc.
        bloc = Text()
        bloc.append("LuluCode ", style=f"bold {SECONDAIRE}")
        bloc.append(version, style=SECONDAIRE)
        bloc.append("  |  profil ", style=SECONDAIRE)
        bloc.append(profil, style=SECONDAIRE)
        bloc.append("  |  mode ", style=SECONDAIRE)
        bloc.append(mode, style=SECONDAIRE)
        bloc.append("  |  dossier ", style=SECONDAIRE)
        bloc.append(dossier, style=SECONDAIRE)
        self.console.print(bloc)
        self.console.print()

    def invite(self) -> str:
        return "> "

    # --- réponses ----------------------------------------------------------

    def texte_agent(self, texte: str) -> None:
        """Réponse de l'agent en Markdown rendu.

        Titres, listes, gras, citations et blocs de code colorés :
        pareil aux agents de code modernes dans le terminal.
        """
        from rich.markdown import Markdown

        self.console.print(Markdown(texte or ""))

    def curseur(self, actif: bool) -> None:
        """Curseur d'écriture cyan : séquence OSC 12 (Windows Terminal,
        iTerm2, kitty...) ; sans effet ailleurs, sans exception.
        """
        try:
            import sys as _sys

            if not self.console.is_terminal:
                return
            # OSC 12 : change la couleur du curseur du terminal.
            _sys.stdout.write(f"\x1b]12;{CYAN}\x07")
            _sys.stdout.flush()
        except Exception:
            pass  # terminal non compatible : aucun effet, aucune erreur

    # --- actions outil ---------------------------------------------------

    def outil(self, nom: str, cible: str) -> None:
        """Ligne ⏺ colorée par niveau (vert lecture, jaune commande,
        rouge niveau 3), libellé dim et cible en blanc.
        """
        from rich.text import Text

        niveau = int(_niveau_outil(nom))
        etiquette = _ETIQUETTES.get(nom, "outil")
        couleur = (VERT, JAUNE, JAUNE, ROUGE)[max(0, min(3, niveau))]
        bloc = Text()
        bloc.append(f"  {GLYPHE} ", style=f"bold {couleur}")
        bloc.append(f"{etiquette}", style=SECONDAIRE)
        if cible:
            bloc.append(" · ", style=SECONDAIRE)
            bloc.append(cible, style=TEXTE)
        self.console.print(bloc)

    def diff(self, chemin: str, texte_diff: str) -> None:
        """Bloc de différence encadré, + en vert, - en rouge."""
        from rich.panel import Panel
        from rich.text import Text

        bloc = Text()
        lignes = texte_diff.splitlines()
        for i, ligne in enumerate(lignes):
            final = "" if i == len(lignes) - 1 else "\n"
            if ligne.startswith("+"):
                bloc.append(f"{ligne}{final}", style=VERT)
            elif ligne.startswith("-"):
                bloc.append(f"{ligne}{final}", style=ROUGE)
            elif ligne.startswith("@@"):
                bloc.append(f"{ligne}{final}", style=SECONDAIRE)
            else:
                bloc.append(f"{ligne}{final}", style=TEXTE)
        self.console.print(
            Panel(
                bloc,
                title=Text(chemin, style=SECONDAIRE),
                border_style=BORDE,
                style=f"on {PANNEAU}",
                padding=(0, 2),
            )
        )

    # --- contrôles ---------------------------------------------------------

    def erreur(self, message: str) -> None:
        from rich.text import Text

        bloc = Text()
        bloc.append(f"  {GLYPHE} ", style=f"bold {ROUGE}")
        bloc.append("erreur · ", style=ROUGE)
        bloc.append(message, style=TEXTE)
        self.console.print(bloc)

    def permission(self, demande: dict[str, Any]) -> str:
        from rich.panel import Panel
        from rich.prompt import Prompt
        from rich.text import Text

        niveau = int(demande["niveau"])
        # Gabarit du rectangle jaune de terminal.svg, en Text pour éviter
        # l'interprétation du détail (arguments JSON) comme balises.
        corps = Text()
        corps.append("Autoriser ", style=f"bold {JAUNE}")
        corps.append(str(demande["outil"]), style=f"bold {JAUNE}")
        corps.append(f" (niveau {niveau}) — {demande['raison']}\n", style=f"bold {JAUNE}")
        corps.append(f"{demande.get('detail', '')}\n\n", style=TEXTE)
        corps.append("[o] ", style=f"bold {VERT}")
        corps.append("une fois      ", style=TEXTE)
        corps.append("[s] ", style=f"bold {BLEU}")
        corps.append("pour la session      ", style=TEXTE)
        corps.append("[n] ", style=f"bold {ROUGE}")
        corps.append("refuser", style=TEXTE)
        self.console.print(
            Panel(
                corps,
                border_style=JAUNE,
                style=f"on {FOND}",
                title=Text(f"permission — niveau {niveau}", style=JAUNE),
                padding=(0, 2),
            )
        )
        return Prompt.ask(
            "  Votre choix",
            choices=["o", "s", "n"],
            default="n",
            show_choices=False,
            console=self.console,
        )

    def plafond(self, raison: str) -> None:
        from rich.text import Text

        bloc = Text()
        bloc.append(f"  {GLYPHE} ", style=f"bold {JAUNE}")
        bloc.append("plafond · ", style=JAUNE)
        bloc.append(raison, style=SECONDAIRE)
        self.console.print(bloc)

    def au_revoir(self) -> None:
        from rich.text import Text

        bloc = Text()
        bloc.append("À bientôt.", style=SECONDAIRE)
        self.console.print(bloc)


def _niveau_outil(nom: str) -> int:
    """Niveau de risque de l'outil, pour colorer le glyphe (0 à 3)."""
    try:
        from lulucode.core.agent import OUTILS

        return int(OUTILS[nom]["niveau"])
    except Exception:
        return 0


def cree_rendu() -> RenduSimple | RenduRiche:
    """Rich si disponible, sinon le rendu sobre."""
    try:
        import rich  # noqa: F401
    except ImportError:
        return RenduSimple()
    return RenduRiche()
