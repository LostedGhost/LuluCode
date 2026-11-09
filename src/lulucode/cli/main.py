"""Façade terminal de LuluCode.

N'affiche que des événements et renvoie les réponses de l'utilisateur :
toute la logique est dans le cœur.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click

import lulucode


@click.group()
@click.version_option(package_name="lulucode")
def app() -> None:
    """LuluCode : un agent de code qui tourne chez vous."""


@click.group()
def config() -> None:
    """Gère la configuration de LuluCode."""


@config.command("init")
def config_init() -> None:
    """Crée le fichier de configuration avec un profil local Ollama."""
    from lulucode.model.client import ecrit_config_exemple

    chemin = Path(
        os.environ.get("LULUCODE_CONFIG", "~/.config/lulucode/config.toml")
    ).expanduser()
    if chemin.is_file():
        click.echo(f"Configuration déjà présente : {chemin}", err=True)
        sys.exit(1)
    ecrit_config_exemple(chemin)
    click.echo(f"Configuration créée : {chemin}")
    click.echo("Éditez ensuite le nom du modèle, puis lancez lulucode dans votre projet.")


@app.command()
@click.option("--profil", "-p", default=None, help="(ancien nom) profil de modèle pour cette session")
@click.option("--mode", "-m", default="normal", help="Mode de permission : normal, strict, lecture-seule")
@click.option("--tache", "-t", default=None, help="Exécute cette tâche unique puis quitte")
@click.argument("profil_positionne", required=False, default=None)
def run(profil: str | None, mode: str, tache: str | None, profil_positionne: str | None) -> None:
    """Démarre une session dans le terminal, dans le dossier courant.

    Le nom de profil se passe directement : `lulucode run distant`.
    Sans argument, c'est le profil par défaut de la configuration.
    """
    from lulucode.cli.render import cree_rendu
    from lulucode.model.client import ClientModele, charge_config, profil_actif
    from lulucode.permissions.moteur import Mode

    rendu = cree_rendu()
    seule = Path.cwd()
    nom_profil = profil_positionne or profil
    try:
        config = charge_config()
        p = profil_actif(config, nom_profil)
    except (FileNotFoundError, ValueError) as e:
        rendu.erreur(str(e))
        sys.exit(1)

    try:
        mode_perm = Mode(mode)
    except ValueError:
        rendu.erreur(f"Mode inconnu : {mode} (normal, strict, lecture-seule)")
        sys.exit(1)

    rendu.etat(lulucode.__version__, p.nom, mode_perm.value, str(seule))

    from lulucode.core.agent import Agent, Plafonds
    from lulucode.permissions.moteur import Moteur

    general = config.get("general", {})
    agent = Agent(
        client=ClientModele(p),
        zone=seule,
        moteur=Moteur(mode=mode_perm, sures=config.get("permissions", {}).get("commandes_sures", [])),
        plafonds=Plafonds(
            etapes=int(general.get("plafond_etapes", 40)),
            tokens=int(general.get("plafond_tokens", 200_000)),
        ),
    )

    asyncio.run(_ou_mono_tache(agent, tache, rendu))


async def _ou_mono_tache(agent: object, tache: str | None, rendu: object) -> None:
    """Exécute une tâche unique si donnée, sinon lance la session plein écran.

    Affichage simple : la réponse complète arrive d'un bloc (pas de
    streaming), affichée une seule fois via l'événement TEXTE.
    """
    if tache and tache.strip() and not veut_sortir(tache):
        await agent.execute(
            tache, emetteur=_EmetteurTerminal(rendu), permission=_permission_terminal(rendu)
        )
        return
    from lulucode.cli.session import Session

    session = Session(
        agent, rendu, version=lulucode.__version__,
        profil=str(getattr(agent, "client").profil.nom),
        mode=str(getattr(agent, "moteur").mode.value),
    )
    await session.boucle()


"""Sortie de session : « exit » (ou « quit », « /quitter », « /exit »),
insensible à la casse et aux espaces, coupe l'agent.
"""
_MOTS_SORTIE = frozenset({"exit", "quit", "quitter", "/exit", "/quit", "/quitter"})


def veut_sortir(texte: str) -> bool:
    """True si la saisie demande la fin de la session."""
    return texte.strip().lower() in _MOTS_SORTIE


async def _boucle_session(agent: object, rendu: object) -> None:
    """Boucle interactive : l'utilisateur tape une tâche, le cœur s'exécute.

    La réponse est déjà émise par l'émetteur via l'événement TEXTE ; la
    valeur de retour n'est jamais réaffichée (sinon duplication).
    """
    import click

    rendu.banniere(lulucode.__version__, "", "")
    rendu.curseur(True)  # curseur d'écriture cyan tant que la session tourne
    while True:
        try:
            tache = click.prompt(click.style(rendu.invite(), fg="cyan", bold=True),
                                  default="", show_default=False)
        except (KeyboardInterrupt, EOFError):
            rendu.curseur(False)
            rendu.au_revoir()
            return
        if veut_sortir(tache):
            rendu.curseur(False)
            rendu.au_revoir()
            return
        if not tache.strip():
            continue
        if tache.strip().lower() == "/aide":
            rendu.texte_agent(
                "**Commandes disponibles**\n\n"
                "- `/aide` — cette liste\n"
                "- `exit` ou `/quitter` — sortir de la session"
            )
            continue
        if tache.strip().lower() == "/journal":
            rendu.texte_agent("*(à venir : journal des actions)*")
            continue
        rendu.curseur(False)  # pas de curseur barre pendant l'exécution
        await agent.execute(
            tache, emetteur=_EmetteurTerminal(rendu), permission=_permission_terminal(rendu)
        )
        rendu.curseur(True)


class _EmetteurTerminal:
    """Affiche les événements du cœur dans le terminal, style des SVG."""

    def __init__(self, rendu: object) -> None:
        self.rendu = rendu

    def emettre(self, evenement: object) -> None:
        from lulucode.core.events import Kind

        if evenement.type is Kind.TEXTE:
            # En streaming, le fragment a déjà été écrit au fil de l'eau ;
            # on n'imprime ici qu'en mode non-streamé (deja_affiche absent).
            if not evenement.donnees.get("deja_affiche"):
                self.rendu.texte_agent(evenement.donnees.get("texte", ""))
        elif evenement.type is Kind.OUTIL_APPEL:
            args = evenement.donnees.get("arguments", {})
            # Cible lisible au gabarit des SVG : le chemin ou la commande
            # d'abord, sinon un résumé compact des arguments.
            cible = (args.get("chemin") or args.get("commande")
                     or args.get("motif") or ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items()))
            self.rendu.outil(evenement.donnees.get("outil", ""), str(cible))
        elif evenement.type is Kind.OUTIL_RESULTAT:
            pass  # déjà affiché via OUTIL_APPEL / DIFF
        elif evenement.type is Kind.DIFF:
            self.rendu.diff(evenement.donnees.get("chemin", ""), evenement.donnees.get("diff", ""))
        elif evenement.type is Kind.PLAFOND:
            self.rendu.plafond(str(evenement.donnees.get("raison", "")))
        elif evenement.type is Kind.ERREUR:
            self.rendu.erreur(str(evenement.donnees.get("message", "")))


def _permission_terminal(rendu: object):
    """Demande à l'utilisateur : une fois / pour la session / refuser.

    Le cœur mémorise l'autorisation pour la session après une réponse True ;
    le niveau 3 n'est jamais mémorisé (garantie du moteur).
    """
    async def _demande(demande: dict) -> bool:
        choix = rendu.permission(demande)
        return choix in ("o", "s")

    return _demande


@app.command()
@click.option("--version-cible", "-v", default=None,
              help="Installer cette version précise (tag git ou numéro PyPI)")
@click.argument("version_positionnee", required=False, default=None)
def update(version_cible: str | None, version_positionnee: str | None) -> None:
    """Met lulucode à jour, ou installe une version précise."""
    from lulucode.cli.render import cree_rendu
    from lulucode.cli.update import liste_versions, mets_a_jour, version_actuelle

    rendu = cree_rendu()
    version = version_cible or version_positionnee

    if not version:
        rendu.texte_agent(f"Version actuelle : {version_actuelle()}")
        disponibles = liste_versions()
        if disponibles and disponibles[-1] != version_actuelle():
            rendu.texte_agent(f"Versions disponibles : {', '.join(disponibles)}")
        elif disponibles:
            rendu.texte_agent("Aucune autre version disponible.")

    code, journal = mets_a_jour(version)
    for ligne in journal:
        rendu.texte_agent(f"  {ligne}") if not ligne.startswith("installation") else rendu.texte_agent(ligne)
    sys.exit(code)


app.add_command(config)


if __name__ == "__main__":
    app()
