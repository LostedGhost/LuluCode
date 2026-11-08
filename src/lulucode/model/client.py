"""Client modèle : API au format OpenAI, profils, validation des appels d'outils.

Le client parle à Ollama (`http://localhost:11434/v1`) comme à un service
distant : c'est le profil qui change, jamais le code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


@dataclass(slots=True)
class Profil:
    """Un profil de modèle dans la configuration TOML."""

    nom: str
    base_url: str
    model: str
    api_key: str = "ollama"
    contexte: int = 8192
    outils_natifs: bool = True


@dataclass(slots=True)
class ReponseModele:
    """Réponse du modèle : du texte, un appel d'outil, ou les deux."""

    texte: str = ""
    outil: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)


class ErreurModele(Exception):
    """Échec d'appel au modèle (réseau, format, clé)."""


def charge_config(chemin: Path | None = None) -> dict[str, Any]:
    """Lit `~/.config/lulucode/config.toml` (ou le chemin donné)."""
    import tomllib

    chemin = chemin or Path(
        os.environ.get("LULUCODE_CONFIG", "~/.config/lulucode/config.toml")
    ).expanduser()
    if not chemin.is_file():
        raise FileNotFoundError(
            f"configuration introuvable : {chemin} — lancez `lulucode config init`"
        )
    with chemin.open("rb") as f:
        return tomllib.load(f)


def profil_actif(config: dict[str, Any], nom: str | None = None) -> Profil:
    """Retourne le profil demandé, ou le profil par défaut."""
    profils = config.get("profils", {})
    if not profils:
        raise ValueError("aucun profil défini dans la configuration")
    nom = nom or os.environ.get("LULUCODE_PROFIL") or config.get("general", {}).get(
        "profil_par_defaut"
    )
    if nom not in profils:
        raise ValueError(f"profil inconnu : {nom!r} (disponibles : {', '.join(profils)})")
    donnees = profils[nom]
    cle_env = donnees.get("api_key_env")
    cle = os.environ[cle_env] if cle_env else donnees.get("api_key", "ollama")
    return Profil(
        nom=nom,
        base_url=donnees["base_url"],
        model=donnees["model"],
        api_key=cle,
        contexte=int(donnees.get("contexte", 8192)),
        outils_natifs=bool(donnees.get("outils_natifs", True)),
    )


def ecrit_config_exemple(chemin: Path) -> None:
    """Écrit une configuration de départ avec un profil local Ollama."""
    import tomli_w

    chemin.parent.mkdir(parents=True, exist_ok=True)
    contenu: dict[str, Any] = {
        "profils": {
            "local": {
                "base_url": "http://localhost:11434/v1",
                "model": "nom-du-modele-local",
                "api_key": "ollama",
                "contexte": 8192,
                "outils_natifs": True,
            }
        },
        "general": {
            "profil_par_defaut": "local",
            "plafond_etapes": 40,
            "plafond_tokens": 200_000,
        },
    }
    with chemin.open("wb") as f:
        tomli_w.dump(contenu, f)


def valide_appel(outil: str | None, arguments: Any, outils_connus: set[str]) -> str | None:
    """Valide un appel d'outil avant exécution. Renvoie None si valide,
    sinon un message d'erreur court à renvoyer au modèle.
    """
    if outil is None:
        return None
    if outil not in outils_connus:
        return f"outil inconnu : {outil!r}. Outils disponibles : {', '.join(sorted(outils_connus))}"
    if not isinstance(arguments, dict):
        return "les arguments doivent être un objet JSON"
    return None


class ClientModele:
    """Client minimal au format OpenAI pour l'API chat/completions."""

    def __init__(self, profil: Profil, *, delai_s: float = 120.0) -> None:
        self.profil = profil
        self._client = httpx.Client(
            base_url=profil.base_url,
            headers={"Authorization": f"Bearer {profil.api_key}"},
            timeout=delai_s,
        )

    def completions(
        self,
        messages: list[dict[str, Any]],
        outils: list[dict[str, Any]] | None = None,
        *,
        sur_ecriture: Any | None = None,
    ) -> ReponseModele:
        """Appelle le modèle et extrait texte ou appel d'outil.

        Avec `sur_ecriture` (callable recevant chaque fragment de texte),
        l'appel est en streaming : le texte s'affiche au fur et à mesure,
        comme sur les agents modernes. Si le serveur ne tient pas le
        format SSE, on retombe silencieusement sur un appel normal.
        """
        if sur_ecriture is not None:
            try:
                return self._completions_stream(
                    messages, outils, sur_ecriture
                )
            except ErreurModele:
                raise
            except Exception:
                pass  # format SSE non tenu : repli normal
        return self._completions_normal(messages, outils)

    def _completions_normal(
        self,
        messages: list[dict[str, Any]],
        outils: list[dict[str, Any]] | None = None,
    ) -> ReponseModele:
        corps: dict[str, Any] = {"model": self.profil.model, "messages": messages}
        if outils:
            corps["tools"] = outils
        try:
            reponse = self._client.post("/chat/completions", json=corps)
            reponse.raise_for_status()
        except httpx.HTTPError as e:
            raise ErreurModele(f"appel du modèle impossible : {e}") from e
        try:
            choix = reponse.json()["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as e:
            raise ErreurModele(f"réponse du modèle illisible : {e}") from e

        outil = choix.get("tool_calls") or []
        if outil:
            appel = outil[0]["function"]
            return ReponseModele(
                texte=choix.get("content") or "",
                outil=appel["name"],
                arguments=json.loads(appel.get("arguments") or "{}"),
            )
        return ReponseModele(texte=choix.get("content") or "")

    def _completions_stream(
        self,
        messages: list[dict[str, Any]],
        outils: list[dict[str, Any]] | None,
        sur_ecriture: Any,
    ) -> ReponseModele:
        """Appel en streaming SSE : chaque fragment est poussé à sur_ecriture.

        Les appels d'outil y sont plus rares (le delta porte alors des
        fragments d'arguments) ; ici on ne streame que le texte pur. Un
        appel d'outil en plein stream bascule le rendu en appel d'outil.
        """
        corps: dict[str, Any] = {
            "model": self.profil.model,
            "messages": messages,
            "stream": True,
        }
        if outils:
            corps["tools"] = outils

        texte: list[str] = []
        outil: str | None = None
        args_str: list[str] = []

        try:
            with self._client.stream("POST", "/chat/completions", json=corps) as flux:
                flux.raise_for_status()
                for ligne in flux.iter_lines():
                    if not ligne or not ligne.startswith("data: "):
                        continue
                    charge = ligne[len("data: "):]
                    if charge.strip() == "[DONE]":
                        break
                    try:
                        morceau = json.loads(charge)
                    except ValueError:
                        continue
                    delta = morceau.get("choices", [{}])[0].get("delta", {})
                    if fragment := delta.get("content"):
                        texte.append(fragment)
                        sur_ecriture(fragment)
                    if appels := delta.get("tool_calls"):
                        premier = appels[0]
                        if fn := premier.get("function", {}).get("name"):
                            outil = fn
                        if args := premier.get("function", {}).get("arguments"):
                            args_str.append(args)
        except httpx.HTTPError as e:
            raise ErreurModele(f"appel du modèle impossible : {e}") from e

        if outil:
            try:
                arguments = json.loads("".join(args_str) or "{}")
            except ValueError:
                arguments = {}
            return ReponseModele(texte="".join(texte), outil=outil, arguments=arguments)
        return ReponseModele(texte="".join(texte))

    def close(self) -> None:
        self._client.close()
