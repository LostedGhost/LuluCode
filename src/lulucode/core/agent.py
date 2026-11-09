"""Boucle d'agent : le cœur unique derrière les deux façades."""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lulucode.core.events import Collecteur, Evenement, Kind, PermissionCallback
from lulucode.model.client import ClientModele, ErreurModele, ReponseModele, valide_appel
from lulucode.permissions.moteur import DecisionValeur, Moteur, Niveau
from lulucode.tools import fichiers
from lulucode.tools.commandes import lance_commande


@dataclass(slots=True)
class Plafonds:
    """Limites d'une tâche : étapes, tokens, secondes."""

    etapes: int = 40
    tokens: int = 200_000
    secondes: int = 600


OUTILS: dict[str, dict[str, Any]] = {
    "lire_fichier": {
        "description": "Lit un fichier de la zone de travail. Niveau 0.",
        "niveau": Niveau.LECTURE,
        "schema": {
            "type": "object",
            "properties": {
                "chemin": {"type": "string", "description": "chemin relatif du fichier"}
            },
            "required": ["chemin"],
        },
    },
    "lister_dossier": {
        "description": "Liste un dossier de la zone de travail. Niveau 0.",
        "niveau": Niveau.LECTURE,
        "schema": {
            "type": "object",
            "properties": {
                "chemin": {"type": "string", "description": "chemin relatif du dossier"}
            },
            "required": ["chemin"],
        },
    },
    "lire_document": {
        "description": (
            "Lit un document non-texte : PDF (texte ou scanné), Word (.docx), "
            "image (PNG/JPG/WebP) transmise au modèle vision si le profil "
            "en a un. Niveau 0. Préférer lire_fichier pour du texte brut."
        ),
        "niveau": Niveau.LECTURE,
        "schema": {
            "type": "object",
            "properties": {
                "chemin": {"type": "string", "description": "chemin relatif du document"},
                "question": {
                    "type": "string",
                    "description": "question facultative sur une image (vision)",
                },
            },
            "required": ["chemin"],
        },
    },
    "chercher_code": {
        "description": "Cherche un motif dans les fichiers de la zone. Niveau 0.",
        "niveau": Niveau.LECTURE,
        "schema": {
            "type": "object",
            "properties": {
                "motif": {"type": "string", "description": "texte à chercher"},
                "glob": {"type": "string", "description": "motif de fichiers, ex. **/*.py"},
            },
            "required": ["motif"],
        },
    },
    "ecrire_fichier": {
        "description": "Crée ou modifie un fichier ; le diff est affiché. Niveau 1.",
        "niveau": Niveau.ECRITURE,
        "schema": {
            "type": "object",
            "properties": {
                "chemin": {"type": "string", "description": "chemin relatif du fichier"},
                "contenu": {"type": "string", "description": "contenu complet du fichier"},
            },
            "required": ["chemin", "contenu"],
        },
    },
    "lancer_commande": {
        "description": "Lance une commande shell dans la zone. Niveau 2.",
        "niveau": Niveau.COMMANDE,
        "schema": {
            "type": "object",
            "properties": {"commande": {"type": "string", "description": "commande à lancer"}},
            "required": ["commande"],
        },
    },
}


def construit_prompt_systeme(
    zone: Path | None = None,
    mode: str | None = None,
) -> str:
    """Charge `systeme/prompt.md` et substitue ses variables.

    Variables du fichier : {{ZONE_DE_TRAVAIL}}, {{OS}}, {{MODE_PERMISSION}},
    {{DATE}}. Les variables inconnues restent telles quelles (pas de
    surprise silencieuse) ; les variables non substituées n'existent plus
    une fois ce module chargé.
    """
    from importlib.resources import files
    import platform
    from datetime import date

    try:
        prompt = (files("lulucode.core") / "systeme" / "prompt.md").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        # Fichier absent (installation partielle) : prompt minimal de secours.
        return (
            "Tu es LuluCode, un agent de code. Tu travailles dans la zone de "
            "travail fournie. Tu lis avant d'écrire, tu proposes un diff avant "
            "de modifier, et tu respectes les décisions de permission qui te "
            "sont renvoyées : un refus impose une autre approche. Réponds en "
            "français."
        )

    substitutions = {
        "{{ZONE_DE_TRAVAIL}}": str((zone or Path.cwd()).resolve()),
        "{{OS}}": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "{{MODE_PERMISSION}}": mode or "normal",
        "{{DATE}}": date.today().isoformat(),
    }
    for variable, valeur in substitutions.items():
        prompt = prompt.replace(variable, valeur)

    # Le prompt référence les modes normal/auto/strict/lecture-seule et
    # bypass : tous sont implémentés par le moteur — pas de note
    # d'alignement nécessaire.
    return prompt


def prompt_avec_skills(prompt_systeme: str, zone: Path | None = None) -> str:
    """Ajoute la liste des skills découverts au prompt système."""
    from lulucode.core.skills import decouvre_skills, liste_pour_modele

    return prompt_systeme + liste_pour_modele(decouvre_skills(zone))



@dataclass
class Agent:
    """Le cœur : reçoit une tâche, appelle le modèle, exécute les outils
    autorisés, émet des événements.

    La permission circule par `PermissionCallback` : une façade l'affiche,
    l'utilisateur répond, la réponse revient sur le même canal. Le cœur ne
    sait pas s'il est piloté par un terminal ou par un navigateur.

    Le system prompt est chargé depuis `systeme/prompt.md` (embarqué dans
    le paquet) et ses variables `{{...}}` sont substituées par l'état
    réel de la session : zone de travail, OS, mode de permission, date.
    Un prompt passé en argument (`systeme=`) remplace entièrement le
    fichier ; pour l'étendre, voir `charge_prompt_systeme`.
    """

    client: ClientModele
    zone: Path
    moteur: Moteur = field(default_factory=Moteur)
    plafonds: Plafonds = field(default_factory=Plafonds)
    systeme: str = field(default_factory=lambda: construit_prompt_systeme())


    async def execute(
        self,
        tache: str,
        *,
        emetteur: Collecteur | Any = None,
        permission: PermissionCallback | None = None,
        sur_ecriture: Any | None = None,
    ) -> str:
        """Exécute une tâche jusqu'à sa fin ou un plafond. Renvoie le texte final.

        Avec `sur_ecriture`, chaque fragment de texte du modèle est poussé
        au fil de l'eau (streaming). L'événement TEXTE n'est alors émis
        qu'une fois par étape, à la fin du flux, avec le texte complet :
        les façades qui streame déjà ne doivent pas réimprimer.
        """
        emetteur = emetteur or Collecteur()
        permission = permission or _permission_refusee
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.systeme},
            {"role": "user", "content": f"Zone de travail : {self.zone.resolve()}\n\nTâche : {tache}"},
        ]
        outils_schema = [
            {"type": "function", "function": {"name": n, "description": d["description"],
                                             "parameters": d["schema"]}}
            for n, d in OUTILS.items()
        ]
        debut = time.monotonic()
        emetteur.emettre(Evenement(Kind.TACHE_DEMARREE, {"tache": tache}))

        for etape in range(1, self.plafonds.etapes + 1):
            try:
                if sur_ecriture is not None:
                    reponse = self.client.completions(
                        messages, outils=outils_schema, sur_ecriture=sur_ecriture
                    )
                    if reponse.texte:
                        # Le fragment a déjà été affiché par la façade :
                        # un événement TEXTE complet la ferait dupliquer.
                        emetteur.emettre(Evenement(
                            Kind.TEXTE, {"texte": reponse.texte, "deja_affiche": True}
                        ))
                else:
                    reponse = self.client.completions(messages, outils=outils_schema)
                    if reponse.texte:
                        emetteur.emettre(Evenement(Kind.TEXTE, {"texte": reponse.texte}))
            except ErreurModele as e:
                emetteur.emettre(Evenement(Kind.ERREUR, {"message": str(e)}))
                return f"erreur modèle : {e}"

            if reponse.outil is None:
                emetteur.emettre(Evenement(Kind.TACHE_TERMINEE, {"etapes": etape}))
                return reponse.texte

            resultat = await self._appelle_outil(reponse, emetteur, permission)

            # Demande de vision (lire_document sur une image) : on relance
            # le modèle avec l'image et la question, sans écrire le
            # base64 dans l'historique.
            if resultat.startswith("__VISION__|"):
                _, mime, base64, question = resultat.split("|", 3)
                vision = await self._comprenne_image(
                    mime, base64, question or "Décris cette image en détail.",
                )
                if vision.startswith("erreur :"):
                    emetteur.emettre(Evenement(Kind.ERREUR, {"message": vision[9:]}))
                    return vision
                emetteur.emettre(Evenement(Kind.TEXTE, {"texte": vision}))
                emetteur.emettre(Evenement(Kind.TACHE_TERMINEE, {"etapes": etape}))
                return vision

            messages.append({"role": "assistant", "content": reponse.texte or "",
                             "tool_calls": _appel_brut(reponse)})
            messages.append({"role": "tool", "tool_call_id": f"{etape}",
                             "content": resultat})

            if time.monotonic() - debut > self.plafonds.secondes:
                emetteur.emettre(Evenement(Kind.PLAFOND, {"raison": "temps"}))
                return "tâche interrompue : plafond de temps atteint"

        emetteur.emettre(Evenement(Kind.PLAFOND, {"raison": "etapes"}))
        return "tâche interrompue : plafond d'étapes atteint"

    async def _appelle_outil(
        self,
        reponse: ReponseModele,
        emetteur: Any,
        permission: PermissionCallback,
    ) -> str:
        """Valide l'appel, demande la permission, exécute si autorisé."""
        erreur = valide_appel(reponse.outil, reponse.arguments, set(OUTILS))
        if erreur:
            emetteur.emettre(Evenement(Kind.ERREUR, {"message": erreur}))
            return f"appel invalide : {erreur}"

        assert reponse.outil is not None
        nom = reponse.outil
        args = reponse.arguments
        schema = OUTILS[nom]
        niveau = schema["niveau"]
        emetteur.emettre(Evenement(Kind.OUTIL_APPEL, {"outil": nom, "arguments": args}))

        # Décision du moteur, puis éventuellement confirmation par la façade.
        # La façade répond True (une fois + mémorisation session), False (refus).
        decision = self.moteur.autoriser(nom, niveau)
        if decision.valeur is DecisionValeur.CONFIRMATION and permission is not None:
            ok = await permission({
                "outil": nom,
                "niveau": int(niveau),
                "raison": decision.raison,
                "detail": json.dumps(args, ensure_ascii=False)[:400],
            })
            if not ok:
                emetteur.emettre(Evenement(Kind.PERMISSION_REPONSE, {"autorise": False}))
                return "action refusée par l'utilisateur. Propose une autre approche."
            self.moteur.memoriser_session(nom, niveau)
            emetteur.emettre(Evenement(Kind.PERMISSION_REPONSE, {"autorise": True}))

        return self._execute_outil(nom, args, emetteur, autorise=True)

    def _execute_outil(self, nom: str, args: dict[str, Any], emetteur: Any, *, autorise: bool) -> str:
        """Exécute l'outil autorisé et émet le résultat.

        Cas particulier `lire_document` sur une image : renvoie le
        marqueur `__VISION__` traité par `execute()` (le contenu binaire
        va au modèle, pas au journal).
        """
        zone = self.zone
        if nom == "lire_fichier":
            r = fichiers.lire_fichier(zone / args["chemin"], zone)
            resultat = r.contenu if r.ok else f"erreur : {r.erreur}"
        elif nom == "lire_document":
            return self._lit_document(args)
        elif nom == "lister_dossier":
            r = fichiers.lister_dossier(zone / args["chemin"], zone)
            resultat = r.contenu if r.ok else f"erreur : {r.erreur}"
        elif nom == "chercher_code":
            r = fichiers.chercher_dans_code(args["motif"], zone, glob=args.get("glob", "**/*"))
            resultat = r.contenu if r.ok else f"erreur : {r.erreur}"
        elif nom == "ecrire_fichier":
            r = fichiers.ecrire_fichier(
                zone / args["chemin"], args["contenu"], zone, autorise=autorise
            )
            if r.ok:
                emetteur.emettre(Evenement(Kind.DIFF, {"chemin": args["chemin"], "diff": r.diff}))
            resultat = r.diff if r.ok else f"erreur : {r.erreur or r.diff}"
        elif nom == "lancer_commande":
            commande = args["commande"]
            decision = self.moteur.autoriser_commande(commande)
            if decision.valeur is DecisionValeur.REFUSE:
                resultat = f"commande refusée ({decision.raison})"
                autorise = False
            elif decision.valeur is DecisionValeur.CONFIRMATION:
                # La demande de permission a déjà été faite de façon
                # générale dans _appelle_outil (niveau 2) : si on arrive
                # ici, c'est que la façade a autorisé le niveau mais que
                # le moteur veut une confirmation spécifique à la
                # commande. On refuse sobrement pour éviter un doublon
                # de demande.
                resultat = "commande à confirmer : relance la demande via l'outil"
                autorise = False
            else:
                r = lance_commande(commande, zone, autorise=True)
                resultat = r.sortie if r.ok else f"erreur : {r.erreur}"
                if r.ok and not resultat:
                    resultat = f"(code {r.code_retour}, aucune sortie)"
        else:
            resultat = f"outil non implémenté : {nom}"
        emetteur.emettre(Evenement(Kind.OUTIL_RESULTAT, {"outil": nom, "resultat": resultat}))
        return resultat

    def _comprenne_image(self, mime: str, base64: str, question: str) -> str:
        """Vision : relance le modèle avec l'image en base64.

        Un seul tour : l'image + la question, réponse texte directe
        (pas d'appel d'outil attendu dans ce tour).
        """
        try:
            reponse = self.client.completions(
                [{"role": "user", "content": question}],
                images=[{"mime": mime, "base64": base64}],
            )
        except ErreurModele as e:
            return f"erreur : vision impossible ({e})"
        return reponse.texte or "(le modèle n'a rien renvoyé pour cette image)"

    def _lit_document(self, args: dict[str, Any]) -> str:
        """Route lire_document : texte extrait, ou demande de vision.

        Renvoie soit le contenu texte, soit `__VISION__|chemin|mime|question`
        — ce marqueur est intercepté par execute() qui relance le modèle
        avec l'image (uniquement si le profil le permet).
        """
        from lulucode.tools.documents import lit_document, données_image_base64, type_de_document

        chemin = self.zone / args["chemin"]
        question = str(args.get("question", "") or "")
        r = lit_document(
            chemin, self.zone,
            profil_vision=self.client.profil.vision,
            question=question,
        )
        if not r.ok:
            return f"erreur : {r.erreur}"
        if r.contenu:
            return r.contenu  # texte extrait (pdf/docx)
        # Image + profil vision : le binaire va au modèle via le marqueur.
        if (donnees := données_image_base64(chemin)) is not None:
            mime, base64 = donnees
            return f"__VISION__|{mime}|{base64}|{question}"
        return "erreur : image illisible"


def _appel_brut(reponse: ReponseModele) -> list[dict[str, Any]]:
    """Reconstitue l'appel d'outil brut pour l'historique des messages."""
    return [{
        "id": "appel",
        "type": "function",
        "function": {"name": reponse.outil, "arguments": json.dumps(reponse.arguments)},
    }]


async def _permission_refusee(demande: dict[str, Any]) -> bool:
    """Callback de secours : refuse toute confirmation non branchée."""
    return False
