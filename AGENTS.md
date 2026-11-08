# AGENTS.md — guide pour les agents IA travaillant sur LuluCode

## Ce que ce projet est

LuluCode est un agent de code open source qui tourne en local, au format
d'API OpenAI (Ollama ou service distant). Un cœur Python sans interface,
deux façades (terminal, web). La pièce centrale est le moteur de
permissions : **aucune action n'est exécutée sans qu'une règle l'ait
autorisée**.

## Structure

```
src/lulucode/
  core/           events.py (contrat d'événements), agent.py (boucle d'agent)
  model/          client.py (client OpenAI, profils, validation)
  tools/          fichiers.py, commandes.py
  permissions/    moteur.py (niveaux, modes, décisions, zone de travail)
  cli/            main.py (façade terminal, Click)
tests/            test_moteur.py, test_fichiers.py, test_agent.py
```

## Règles non négociables

1. **Niveau 3 jamais automatisé.** Une action de niveau `Niveau.DESTRUCTIF`
   ne doit jamais être exécutée sans confirmation humaine, jamais mémorisée
   pour la session (le moteur lève `ValueError` sur une tentative de
   mémorisation). Tout changement touchant aux permissions s'accompagne de
   tests qui prouvent cet invariant.
2. **Une seule décision : le moteur.** Les outils ne décident de rien ;
   ils reçoivent `autorise=False/True` du cœur, qui l'obtient du moteur.
3. **Zone de travail.** Tout chemin passe par `resous_dans_zone` (résolution
   des liens symboliques). Un accès extérieur est de niveau 3.
4. **Un cœur, deux façades.** Aucune logique métier dans `cli/` (ni plus
   tard `server/`) : les façades affichent des `Evenement` et renvoient des
   réponses. Une nouvelle fonctionnalité va dans le cœur.
5. **Séparations des responsabilités** : permissions (`permissions/`) et
   exécution (`tools/`) ne se mélangent pas.

## Conventions

- Langue : identifiants en français, docstrings en français, court et précis.
- Typage strict (mypy), imports triés (ruff `I`), ligne ≤ 100.
- Tests avec pytest + pytest-asyncio, modèles réels jamais appelés :
  utiliser `ModeleFictif` (voir `tests/test_agent.py`).
- Commits : préfixes `feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`.

## Commandes

```bash
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -e ".[dev]"
pytest                          # tests complets
ruff check src tests            # style
mypy src                        # typage
```

## État (v0.1.0)

Implémenté : boucle d'agent + contrat d'événements, client format OpenAI
avec profils, outils lecture/liste/cherche/écrit/commande, moteur de
permissions (niveaux 0-3, modes normal/strict/lecture-seule, mémorisation
session, zone de travail), façade terminal Click, tests moteur + outils +
boucle avec modèle fictif.

Non fait (feuille de route README) : façade web (FastAPI + React + SSE),
DocScan, recherche web, résumé des longues conversations, mode de secours
pour modèles sans appels d'outils natifs, paquet PyPI.
