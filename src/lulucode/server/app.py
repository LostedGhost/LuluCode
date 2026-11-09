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
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from lulucode.core.events import Evenement, Kind


class SessionWeb:
    """Une session web : agent, file d'événements (SSE), permissions."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.file: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.futures_permission: dict[str, asyncio.Future] = {}
        self._compteur_permission = 0
        self.tache_en_cours = False

    def publie(self, evenement: Evenement) -> None:
        """Ajoute un événement au flux SSE."""
        self.file.put_nowait({
            "type": evenement.type.value,
            "donnees": evenement.donnees,
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


def configure(agent: Any, port: int = 8341) -> str:
    """Branche l'agent au serveur, renvoie l'URL d'accès."""
    global session_active
    session_active = SessionWeb(agent)
    return f"http://127.0.0.1:{port}/"


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

_PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LuluCode</title>
<style>
  :root {
    --fond:#0d1117; --panneau:#161b22; --bordure:#30363d;
    --texte:#e6edf3; --gris:#8b949e; --cyan:#22d3ee; --violet:#a78bfa;
    --vert:#3fb950; --bleu:#58a6ff; --jaune:#d29922; --rouge:#f85149;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--fond); color:var(--texte);
         font:15px/1.5 'Segoe UI', Roboto, sans-serif;
         display:flex; flex-direction:column; height:100vh; }
  header { display:flex; align-items:center; gap:12px;
           padding:10px 18px; border-bottom:1px solid var(--bordure);
           background:var(--panneau); }
  .logo { font-weight:800; color:var(--cyan); letter-spacing:.5px; }
  .etat { color:var(--gris); font-size:13px; }
  #journal { flex:1; overflow-y:auto; padding:18px; max-width:920px;
             width:100%; margin:0 auto; }
  .bloc { margin-bottom:14px; line-height:1.55; white-space:pre-wrap; }
  .utilisateur { color:var(--texte); }
  .chevron { color:var(--cyan); font-weight:700; }
  .agent { color:var(--texte); }
  .outil { color:var(--gris); font-size:14px; margin:10px 0; }
  .point-l { color:var(--vert); margin-right:8px; }
  .point-erreur { color:var(--rouge); margin-right:8px; }
  .erreur { color:var(--rouge); }
  .plafond { color:var(--jaune); font-size:14px; }
  .diff { background:var(--panneau); border:1px solid var(--bordure);
          border-radius:10px; padding:10px 14px;
          font-family:Consolas, monospace; font-size:13px; }
  .diff .plus { color:var(--vert); }
  .perm { border:1px solid var(--jaune); background:rgba(210,153,34,.07);
          border-radius:10px; padding:12px 16px; margin:12px 0; }
  .perm .titre { font-weight:700; color:var(--jaune); margin-bottom:6px; }
  .perm .detail { font-family:Consolas, monospace; font-size:12.5px;
                  color:var(--gris); margin-bottom:10px;
                  white-space:pre-wrap; word-break:break-all; }
  .perm button { cursor:pointer; border-radius:8px; padding:6px 14px;
                 font-size:13px; margin-right:8px; background:transparent;
                 border:1px solid var(--bordure); color:var(--texte); }
  .perm .oui { border-color:var(--vert); color:var(--vert); }
  .perm .oui-session { border-color:var(--bleu); color:var(--bleu); }
  .perm .non { border-color:var(--rouge); color:var(--rouge); }
  form.envoi { display:flex; gap:10px; padding:12px 18px;
               border-top:1px solid var(--bordure); background:var(--panneau); }
  form.envoi input { flex:1; background:var(--fond); color:var(--texte);
                     border:1px solid var(--bordure); border-radius:8px;
                     padding:10px 12px; font-size:15px; }
  form.envoi input:focus { outline:1px solid var(--cyan); }
  form.envoi button { background:var(--cyan); color:#0d1117; border:0;
                      border-radius:8px; padding:0 18px; font-weight:700;
                      cursor:pointer; }
  form.envoi button:disabled { opacity:.4; cursor:default; }
</style>
</head>
<body>
<header>
  <span class="logo">LuluCode</span>
  <span class="etat" id="etat">connexion…</span>
</header>
<div id="journal"></div>
<form class="envoi" id="formulaire">
  <input id="saisie" placeholder="Décrivez une tâche · exit pour sortir"
         autocomplete="off" autofocus>
  <button id="bouton-envoi" type="submit">Envoyer</button>
</form>
<script>
const journal = document.getElementById('journal');
const etat = document.getElementById('etat');

function echappe(t) { const d = document.createElement('div');
                      d.textContent = t == null ? '' : String(t);
                      return d.innerHTML; }

function ajoute(html, classe) {
  const div = document.createElement('div');
  div.className = 'bloc ' + (classe || '');
  div.innerHTML = html;
  journal.appendChild(div);
  journal.scrollTop = journal.scrollHeight;
}

// --- envoi de tâche ---
document.getElementById('envoi').addEventListener('submit', async (e) => {
  e.preventDefault();
  const champ = document.getElementById('saisie');
  const texte = champ.value.trim();
  champ.value = '';
  if (!texte) return;
  if (/^(exit|quit|quitter|\\/exit|\\/quit|\\/quitter)$/i.test(texte)) {
    ajoute('<span class="chevron">&gt;</span>', 'utilisateur');
    ajoute('Session terminée du côté de la page. Le serveur reste actif, '
           + 'arrêtez-le par Ctrl+C dans le terminal.', 'agent');
    return;
  }
  ajoute('<span class="chevron">&gt;</span> ' + echappe(texte), 'utilisateur');
  document.getElementById('bouton-envoi').disabled = true;
  etat.textContent = 'agent en action…';
  const reponse = await fetch('/tache', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({tache: texte}),
  });
  if (!reponse.ok) {
    const err = await reponse.json().catch(() => ({detail:'erreur'}));
    ajoute('⛔ ' + echappe(err.detail || 'échec'), 'erreur');
    document.getElementById('bouton-envoi').disabled = false;
    etat.textContent = 'prêt';
  }
});

// --- flux SSE ---
const source = new EventSource('/evenements');
source.onmessage = (e) => {
  let ev; try { ev = JSON.parse(e.data); } catch { return; }
  const d = ev.donnees || {};
  switch (ev.type) {
    case 'connecte': etat.textContent = 'prêt'; break;
    case 'texte':
      if (d.deja_affiche) break;
      ajoute(echappe(d.texte || ''), 'agent');
      break;
    case 'outil_appel': {
      const a = d.arguments || {};
      const cible = a.chemin || a.commande || a.motif
                    || Object.values(a).join(', ');
      ajoute('<span class="point-l">⏺</span>'
             + echappe(d.outil || '') + ' · ' + echappe(cible), 'outil');
      break;
    }
    case 'diff': {
      const lignes = echappe(d.diff || '').split('\\n').map((l) =>
        l.startsWith('+') ? '<span class="plus">' + l + '</span>'
        : l.startsWith('-') ? '<span style="color:var(--rouge)">' + l + '</span>'
        : l).join('\\n');
      ajoute('<div class="diff"><b>' + echappe(d.chemin || '') + '</b>\\n' + lignes
             + '</div>', 'agent');
      break;
    }
    case 'permission_demandee': {
      const bloc = document.createElement('div');
      bloc.className = 'perm';
      bloc.innerHTML =
        '<div class="titre">Autoriser ' + echappe(d.outil) + ' (niveau '
        + echappe(String(d.niveau)) + ') ?</div>'
        + '<div class="detail">' + echappe(d.detail || '') + '</div>'
        + '<button class="oui" data-i="' + d.id + '">[o] une fois</button>'
        + '<button class="oui-session" data-i="' + d.id + '">[s] session</button>'
        + '<button class="non" data-i="' + d.id + '">[n] refuser</button>';
      bloc.querySelectorAll('button').forEach((b) => {
        b.addEventListener('click', async () => {
          b.disabled = true;
          await fetch('/permission', {method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({identifiant: b.dataset.i,
                                  accepte: b.classList.contains('oui')})});
          bloc.remove();
        });
      });
      journal.appendChild(bloc);
      journal.scrollTop = journal.scrollHeight;
      break;
    }
    case 'erreur':
      ajoute('<span class="point-erreur">⏺</span> erreur · '
             + echappe(d.message || ''), 'erreur');
      break;
    case 'plafond':
      ajoute('<span class="plafond">plafond · ' + echappe(d.raison || '')
             + '</span>', 'plafond');
      break;
    case 'tache_terminee':
      if (d.source === 'web') break;
      etat.textContent = 'prêt';
      document.getElementById('bouton-envoi').disabled = false;
      break;
  }
};
source.onerror = () => {
  etat.textContent = 'connexion perdue — rechargement…';
  setTimeout(() => location.reload(), 2000);
};
</script>
</body>
</html>"""


def _page_session() -> str:
    return _PAGE


def _page_acces_refuse() -> str:
    return """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>LuluCode</title></head>
<body style="background:#0d1117;color:#e6edf3;font:16px sans-serif;display:flex;
             align-items:center;justify-content:center;height:100vh;margin:0">
<p style="color:#8b949e;max-width:480px;text-align:center">Aucune session active.
Lancez <code>lulucode web</code> dans un terminal, puis ouvrez
<code>http://127.0.0.1:8341/</code>.</p></body></html>"""
