"""Façade web de LuluCode : FastAPI + événements SSE.

Un seul cœur, une deuxième façade : le serveur pilote le même Agent que
le terminal (contrat d'événements identique), avec les demandes de
permission rendues comme boutons dans la page.

Sécurité : écoute uniquement sur 127.0.0.1 (jamais exposé au réseau).
Pas de jeton : l'interface est volontairement immédiate, au prix du
risque résiduel lié aux requêtes cross-origin depuis votre propre
navigateur (opt-out documenté dans le README).

Lancement : `lulucode web [profil] [--mode M] [--port P]`.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from lulucode.core.events import Evenement, Kind


class SessionWeb:
    """Une session web : agent, file d'événements (SSE), permissions.

    Historique multi-tours : chaque échange (tâche utilisateur + réponse
    finale de l'agent) est conservé côté serveur et renvoyé à la page
    au chargement (continuité si on rafraîchit, base de la sidebar).
    """

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.file: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.futures_permission: dict[str, asyncio.Future] = {}
        self._compteur_permission = 0
        self.tache_en_cours = False
        self.historique: list[dict[str, str]] = []  # {role, contenu}
        self.demarrage: str = ""  # première tâche : titre de la conversation
        self.confirmations_session: set[str] = set()

    def publie(self, evenement: Evenement) -> None:
        """Ajoute un événement au flux SSE, en archivant texte et tâche."""
        donnees = dict(evenement.donnees)
        if evenement.type is Kind.TACHE_DEMARREE:
            self.historique.append({"role": "utilisateur", "texte": donnees.get("tache", "")})
            if not self.demarrage:
                self.demarrage = donnees.get("tache", "")[:60]
        elif evenement.type is Kind.TEXTE and not donnees.get("deja_affiche"):
            self.historique.append({"role": "agent", "texte": donnees.get("texte", "")})
        self.file.put_nowait({
            "type": evenement.type.value,
            "donnees": donnees,
        })

    async def demande_permission(self, demande: dict[str, Any]) -> bool:
        """Callback de permission du cœur : pousse via SSE, attend le POST."""
        self._compteur_permission += 1
        identifiant = f"perm-{self._compteur_permission}"
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self.futures_permission[identifiant] = future
        self.publie(Evenement(Kind.PERMISSION_DEMANDEE, {"id": identifiant, **demande}))
        try:
            return bool(await future)
        finally:
            self.futures_permission.pop(identifiant, None)

    async def repond_permission(self, identifiant: str, accepte: bool) -> None:
        future = self.futures_permission.pop(identifiant, None)
        if future is not None and not future.done():
            future.set_result(bool(accepte))

    def emetteur(self) -> "_EmetteurWeb":
        return _EmetteurWeb(self)


class _EmetteurWeb:
    """Traduit les événements du cœur en messages du flux SSE."""

    def __init__(self, session: SessionWeb) -> None:
        self.session = session

    def emettre(self, evenement: Evenement) -> None:
        self.session.publie(evenement)


app = FastAPI(title="LuluCode")

session_active: SessionWeb | None = None

# Bundle React (web/dist/) servi en statique s'il existe.
from fastapi.staticfiles import StaticFiles

_REPERTOIRE_WEB = Path(__file__).parent / "web_dist"
if _REPERTOIRE_WEB.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_REPERTOIRE_WEB / "assets")),
        name="assets",
    )


def configure(agent: Any, port: int = 8341, version: str = "", profil: str = "",
              mode: str = "normal") -> str:
    """Branche l'agent au serveur, renvoie l'URL d'accès."""
    global session_active
    session_active = SessionWeb(agent)
    session_active.profil = profil
    session_active.mode = mode
    session_active.version = version
    return f"http://127.0.0.1:{port}/"


@app.get("/historique")
async def historique() -> dict:
    """Historique de la conversation, pour le rafraîchissement de page."""
    _verifie()
    s = session_active
    return {
        "historique": s.historique,
        "titre": s.demarrage,
        "profil": getattr(s, "profil", ""),
        "mode": getattr(s, "mode", ""),
        "version": getattr(s, "version", ""),
    }


@app.get("/", response_class=HTMLResponse)
async def page() -> HTMLResponse:
    if session_active is None:
        return HTMLResponse(_page_acces_refuse())
    return HTMLResponse(_page_session())


@app.get("/evenements")
async def evenements() -> StreamingResponse:
    """Flux SSE de tous les événements du cœur, au fil de l'eau."""
    _verifie()
    session = session_active

    async def genere():
        yield f"data: {json.dumps({'type': 'connecte'})}\n\n"
        while True:
            evenement = await session.file.get()
            yield f"data: {json.dumps(evenement, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        genere(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


class DemandeTache(BaseModel):
    tache: str


@app.post("/tache")
async def lance_tache(demande: DemandeTache) -> dict:
    _verifie()
    session = session_active
    if session.tache_en_cours:
        raise HTTPException(409, "une tâche est déjà en cours")

    session.tache_en_cours = True
    session.publie(Evenement(Kind.TACHE_DEMARREE, {"tache": demande.tache}))

    async def execute() -> None:
        try:
            await session.agent.execute(
                demande.tache,
                emetteur=session.emetteur(),
                permission=session.demande_permission,
            )
        except Exception as e:  # la façade ne doit jamais mourir en silence
            session.publie(Evenement(Kind.ERREUR, {"message": str(e)}))
        finally:
            session.tache_en_cours = False

    asyncio.create_task(execute())
    return {"statut": "lancee"}


class ReponsePermission(BaseModel):
    identifiant: str
    accepte: bool


@app.post("/permission")
async def repond_permission(demande: ReponsePermission) -> dict:
    _verifie()
    await session_active.repond_permission(demande.identifiant, demande.accepte)
    return {"statut": "ok"}


def _verifie() -> None:
    if session_active is None:
        raise HTTPException(401, "aucune session active (relancez lulucode web)")


# --- pages -------------------------------------------------------------------

# Interface React : bundle construit par `npm run build` dans web/dist/
# puis copié en tant que `web_dist/` du paquet. Retombe sur la page
# légère (page.py) si le bundle n'est pas embarqué.
_REPERTOIRE_WEB = Path(__file__).parent / "web_dist"


def _page_session() -> str:
    index = _REPERTOIRE_WEB / "index.html"
    if index.is_file():
        return index.read_text(encoding="utf-8")
    from lulucode.server.page import PAGE
    return PAGE


def _page_acces_refuse() -> str:
    return """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>LuluCode</title></head>
<body style="background:#0d1117;color:#e6edf3;font:16px sans-serif;display:flex;
             align-items:center;justify-content:center;height:100vh;margin:0">
<p style="color:#8b949e;max-width:480px;text-align:center">Aucune session active.
Lancez <code>lulucode web</code> dans un terminal, puis ouvrez
<code>http://127.0.0.1:8341/</code>.</p></body></html>"""
