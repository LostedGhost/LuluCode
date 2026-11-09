"""Tests de la façade web (httpx ASGI, sans réseau ni modèle réel)."""

import asyncio
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from lulucode.core.events import Evenement, Kind
from lulucode.permissions.moteur import Moteur, Niveau
from lulucode.server.app import SessionWeb, app, configure


class AgentFictif:
    """Agent minimal : émet une demande de permission, puis du texte."""

    def __init__(self, accepte_par_defaut: bool = True) -> None:
        self.zone = Path(".")
        self.moteur = Moteur()
        self.accepte_par_defaut = accepte_par_defaut

    async def execute(self, tache, *, emetteur, permission, sur_ecriture=None) -> str:
        emetteur.emettre(Evenement(
            Kind.OUTIL_APPEL,
            {"outil": "lire_fichier", "arguments": {"chemin": "a.py"}, "niveau": 0},
        ))
        ok = await permission({
            "outil": "ecrire_fichier", "niveau": int(Niveau.ECRITURE),
            "raison": "test", "detail": "{}",
        })
        emetteur.emettre(Evenement(
            Kind.TEXTE, {"texte": f"fin (permission={ok})"}
        ))
        return "fin"


@pytest.fixture()
def session_prete():
    """Session web avec agent fictif, hors HTTP."""
    agent = AgentFictif()
    session = SessionWeb(agent)

    async def _repond_toutes_les_demandes() -> None:
        while True:
            await asyncio.sleep(0.01)
            for identifiant in list(vars(session)) and []:
                pass

    return agent, session


class TestAcces:
    def test_page_sans_serveur_actif(self):
        with TestClient(app) as c:
            reponse = c.get("/")
            assert reponse.status_code == 200
            assert "aucune session" in reponse.text.lower()

    def test_page_configuree_servie(self):
        url = configure(AgentFictif())
        assert "token=" not in url  # option B : pas de jeton
        with TestClient(app) as c:
            reponse = c.get("/")
            assert reponse.status_code == 200
            assert "LuluCode" in reponse.text

    def test_api_sans_session_401(self):
        from lulucode.server import app as module_app

        Sauvegarde = module_app.session_active
        module_app.session_active = None  # état global : test isolé
        try:
            with TestClient(app) as c:
                reponse = c.post("/tache", json={"tache": "x"})
                assert reponse.status_code == 401
        finally:
            module_app.session_active = Sauvegarde


class TestSessionWeb:
    def test_publie_les_evenements_dans_la_file(self):
        session = SessionWeb(AgentFictif())
        session.publie(Evenement(Kind.TEXTE, {"texte": "salut"}))
        message = session.file.get_nowait()
        assert message["type"] == "texte"
        assert message["donnees"]["texte"] == "salut"

    def test_demande_permission_cycle_complet(self):
        """demande_permission pousse l'événement et attend le POST."""
        async def _run():
            session = SessionWeb(AgentFictif())
            tache = asyncio.create_task(
                session.demande_permission({"outil": "ecrire_fichier",
                                            "niveau": 1, "detail": "{}",
                                            "raison": "test"})
            )
            # Laisser la demande arriver dans la file.
            await asyncio.sleep(0.05)
            message = session.file.get_nowait()
            assert message["type"] == "permission_demandee"
            identifiant = message["donnees"]["id"]
            assert str(session._compteur_permission) == identifiant.split("-")[1]
            await session.repond_permission(identifiant, True)
            return await tache

        assert asyncio.run(_run()) is True

    def test_permission_refusee_renvoie_false(self):
        async def _run():
            session = SessionWeb(AgentFictif())
            tache = asyncio.create_task(
                session.demande_permission({"outil": "x", "niveau": 3, "detail": "",
                                            "raison": "r"})
            )
            await asyncio.sleep(0.05)
            message = session.file.get_nowait()
            await session.repond_permission(message["donnees"]["id"], False)
            return await tache

        assert asyncio.run(_run()) is False


class TestTacheRoute:
    def test_post_tache_lance_et_repond(self):
        configure(AgentFictif())
        with TestClient(app) as client:
            reponse = client.post(
                "/tache", json={"tache": "test"}
            )
            assert reponse.status_code == 200
            assert reponse.json()["statut"] == "lancee"

    def test_page_avec_serveur_configure(self):
        configure(AgentFictif())
        with TestClient(app) as client:
            reponse = client.get("/")
            assert reponse.status_code == 200
            assert "LuluCode" in reponse.text

    def test_differenciation_messages_distinguable(self):
        """La page distingue visuellement utilisateur et agent :
        badge « Vous » (bulle dégradé) et badge « LuluCode » (liseré)."""
        configure(AgentFictif())
        from lulucode.server.page import PAGE

        assert 'class="bulle"><span class="qui">Vous' in PAGE
        assert '<span class="qui">LuluCode</span>' in PAGE
        # Bulle utilisateur distincte (dégradé + bord cyan) :
        assert 'linear-gradient(135deg' in PAGE
        # Liseré violet de l'agent :
        assert 'border-left:2px solid rgba(167,139,250' in PAGE

