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


class TestSecurite:
    def test_page_sans_jeton_refusee(self):
        configure(AgentFictif())
        with TestClient(app) as c:
            reponse = c.get("/")
            assert "jeton" in reponse.text.lower()

    def test_api_sans_jeton_refusee(self):
        with TestClient(app) as c:
            assert c.get("/evenements").status_code == 401
            reponse = c.post("/tache", json={"tache": "x"})
            assert reponse.status_code == 401

    def test_page_avec_jeton_servie(self):
        url = configure(AgentFictif())
        token = url.split("token=")[1]
        with TestClient(app) as c:
            reponse = c.get("/", params={"token": token})
            assert reponse.status_code == 200
            assert "LuluCode" in reponse.text


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


class TestRoutes:
    def test_post_tache_sans_jeton(self):
        configure(AgentFictif())
        with TestClient(app) as client:
            assert client.post(
                "/tache", json={"tache": "x"}
            ).status_code == 401

    def test_page_avec_jeton(self):
        url = configure(AgentFictif())
        token = url.split("token=")[1]
        with TestClient(app) as client:
            reponse = client.get("/", params={"token": token})
            assert reponse.status_code == 200
            assert "LuluCode" in reponse.text
