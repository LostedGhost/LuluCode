"""Tests de la boucle d'agent avec un modèle fictif (aucun réseau).

Ces tests vérifient le contrat d'événements et surtout le filet de
sécurité bout en bout : un appel d'outil destructif n'est jamais exécuté
sans confirmation de la façade.
"""

import pytest

from lulucode.core.agent import OUTILS, Agent, Plafonds
from lulucode.core.events import Collecteur, Kind
from lulucode.model.client import ReponseModele, valide_appel
from lulucode.permissions.moteur import Moteur, Niveau


class ModeleFictif:
    """Client modèle de test : rejoue une file de réponses programmées."""

    def __init__(self, reponses: list[ReponseModele]) -> None:
        self.reponses = list(reponses)

    def completions(self, messages, outils=None) -> ReponseModele:
        # Le modèle réagit au résultat renvoyé : refus => il s'arrête.
        dernier = messages[-1]
        if dernier.get("role") == "tool" and "refusée" in dernier.get("content", ""):
            return ReponseModele(texte="J'ai compris, je ne le ferai pas.")
        if len(self.reponses) > 1:
            return self.reponses.pop(0)
        return self.reponses[0]


@pytest.fixture()
def zone(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


class TestValidation:
    def test_outil_inconnu_rejete(self):
        assert "inconnu" in valide_appel("outil_fantome", {}, set(OUTILS))

    def test_arguments_non_dict_rejetes(self):
        assert "objet JSON" in valide_appel("lire_fichier", "pas un dict", set(OUTILS))

    def test_appel_valide(self):
        assert valide_appel("lire_fichier", {"chemin": "a.py"}, set(OUTILS)) is None


class TestBoucle:
    @pytest.mark.asyncio
    async def test_tache_purement_textuelle(self, zone):
        agent = Agent(client=ModeleFictif([ReponseModele(texte="Voilà.")]), zone=zone)
        collecteur = Collecteur()
        final = await agent.execute("dis bonjour", emetteur=collecteur)
        assert final == "Voilà."
        assert collecteur.types(Kind.TACHE_DEMARREE)
        assert collecteur.types(Kind.TACHE_TERMINEE)

    @pytest.mark.asyncio
    async def test_lecture_autorisee_sans_confirmation(self, zone):
        reponse = ReponseModele(outil="lire_fichier", arguments={"chemin": "src/module.py"})
        agent = Agent(client=ModeleFictif([reponse, ReponseModele(texte="fin")]), zone=zone)
        collecteur = Collecteur()
        await agent.execute("lis le fichier", emetteur=collecteur)
        resultat = collecteur.types(Kind.OUTIL_RESULTAT)[0].donnees["resultat"]
        assert "x = 1" in resultat
        # Aucune demande de permission pour une lecture en mode normal.
        assert not collecteur.types(Kind.PERMISSION_DEMANDEE)

    @pytest.mark.asyncio
    async def test_ecriture_refusee_n_ecrit_pas(self, zone):
        cible = zone / "src" / "nouveau.txt"
        reponse = ReponseModele(
            outil="ecrire_fichier", arguments={"chemin": "src/nouveau.txt", "contenu": "pirate"}
        )
        agent = Agent(
            client=ModeleFictif([reponse, ReponseModele(texte="ok j'arrête")]),
            zone=zone,
        )
        collecteur = Collecteur()
        await agent.execute("écris", emetteur=collecteur, permission=async_refuse)
        assert not cible.exists()
        assert collecteur.types(Kind.PERMISSION_REPONSE)[0].donnees["autorise"] is False

    @pytest.mark.asyncio
    async def test_ecriture_confirmee_ecrit_diff(self, zone):
        reponse = ReponseModele(
            outil="ecrire_fichier", arguments={"chemin": "src/mod.py", "contenu": "x = 2\n"}
        )
        agent = Agent(
            client=ModeleFictif([reponse, ReponseModele(texte="fait")]),
            zone=zone,
            moteur=Moteur(),
        )
        collecteur = Collecteur()
        await agent.execute("écris", emetteur=collecteur, permission=async_accepte)
        assert (zone / "src" / "mod.py").read_text(encoding="utf-8") == "x = 2\n"
        diffs = collecteur.types(Kind.DIFF)
        assert diffs and "+x = 2" in diffs[0].donnees["diff"]

    @pytest.mark.asyncio
    async def test_commande_sans_confirmation_n_s_execute_pas(self, zone):
        reponse = ReponseModele(
            outil="lancer_commande", arguments={"commande": "echo echap > ../sortie.txt"}
        )
        agent = Agent(
            client=ModeleFictif([reponse, ReponseModele(texte="arrêté")]),
            zone=zone,
        )
        collecteur = Collecteur()
        await agent.execute("lance", emetteur=collecteur, permission=async_refuse)
        # La commande composée sort de la zone et n'a jamais tourné.
        assert not (zone.parent / "sortie.txt").exists()

    @pytest.mark.asyncio
    async def test_plafond_etapes_arrete_la_boucle(self, zone):
        reponse = ReponseModele(outil="lire_fichier", arguments={"chemin": "src/module.py"})
        agent = Agent(
            client=ModeleFictif([reponse]),
            zone=zone,
            plafonds=Plafonds(etapes=3),
        )
        final = await agent.execute("boucle", emetteur=Collecteur())
        assert "plafond" in final


async def async_accepte(demande) -> bool:
    return True


async def async_refuse(demande) -> bool:
    return False
