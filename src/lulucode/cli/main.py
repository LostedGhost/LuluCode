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
@click.option("--profil", "-p", default=None, help="Profil de modèle pour cette session")
@click.option("--mode", "-m", default="normal", help="Mode de permission : normal, strict, lecture-seule")
@click.option("--tache", "-t", default=None, help="Exécute cette tâche unique puis quitte")
def run(profil: str | None, mode: str, tache: str | None) -> None:
    """Démarre une session dans le terminal, dans le dossier courant."""
    from lulucode.model.client import ClientModele, charge_config, profil_actif
    from lulucode.permissions.moteur import Mode

    seule = Path.cwd()
    try:
        config = charge_config()
        p = profil_actif(config, profil)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Configuration : {e}", err=True)
        sys.exit(1)

    try:
        mode_perm = Mode(mode)
    except ValueError:
        click.echo(f"Mode inconnu : {mode} (normal, strict, lecture-seule)", err=True)
        sys.exit(1)

    click.echo(f"LuluCode {lulucode.__version__}  |  profil {p.nom}  |  mode {mode_perm.value}  |  dossier {seule}")

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

    asyncio.run(_ou_mono_tache(agent, tache))


async def _ou_mono_tache(agent: object, tache: str | None) -> None:
    """Exécute une tâche unique si donnée, sinon lance la boucle interactive."""
    if tache and tache.strip():
        texte = await agent.execute(tache, emetteur=_EmetteurTerminal(), permission=_permission_terminal)
        click.echo(texte if texte else "(terminé)")
        return
    await _boucle_session(agent)


async def _boucle_session(agent: object) -> None:
    """Boucle interactive : l'utilisateur tape une tâche, le cœur s'exécute."""
    while True:
        try:
            tache = click.prompt(click.style(">", fg="cyan", bold=True), default="", show_default=False)
        except (KeyboardInterrupt, EOFError):
            click.echo("\nÀ bientôt.")
            return
        if not tache.strip():
            continue
        if tache == "/aide":
            click.echo("Commandes : /aide (cette liste), /quitter")
            continue
        if tache == "/quitter":
            click.echo("À bientôt.")
            return
        click.echo("…")
        texte = await agent.execute(tache, emetteur=_EmetteurTerminal(), permission=_permission_terminal)
        click.echo(texte if texte else "(terminé)")


class _EmetteurTerminal:
    """Affiche les événements du cœur dans le terminal."""

    def emettre(self, evenement: object) -> None:
        from lulucode.core.events import Kind

        if evenement.type is Kind.TEXTE:
            click.echo(evenement.donnees.get("texte", ""))
        elif evenement.type is Kind.OUTIL_APPEL:
            args = evenement.donnees.get("arguments", {})
            resume = ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())
            click.echo(f"  [outil] {evenement.donnees.get('outil')} {resume}")
        elif evenement.type is Kind.DIFF:
            click.echo(f"  [diff] {evenement.donnees.get('chemin')}")
        elif evenement.type is Kind.ERREUR:
            click.echo(f"  [erreur] {evenement.donnees.get('message')}", err=True)


async def _permission_terminal(demande: dict) -> bool:
    """Demande à l'utilisateur : une fois / pour la session / refuser.

    Le cœur mémorise l'autorisation pour la session après une réponse True ;
    le niveau 3 n'est jamais mémorisé (garantie du moteur).
    """
    from lulucode.permissions.moteur import Niveau

    niveau = Niveau(demande["niveau"])
    click.echo(click.style(f"  [permission] {demande['outil']} (niveau {niveau.value}) — {demande['raison']}", fg="yellow"))
    click.echo(f"  Détail : {demande.get('detail', '')[:200]}")
    while True:
        choix = click.prompt(
            click.style("  [o] une fois  [s] pour la session  [n] refuser", fg="yellow"),
            type=click.Choice(["o", "s", "n"]),
            default="n",
            show_default=False,
        )
        return choix in ("o", "s")


app.add_command(config)


if __name__ == "__main__":
    app()
