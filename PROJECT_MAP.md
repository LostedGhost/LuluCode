# PROJECT_MAP — LuluCode

## Sommaire

Agent de code open source, local-first, au format d'API OpenAI.
Python ≥ 3.11, sans framework. Cœur sans interface + façades.

- **Vitrine** : `README.md` (spéc visée), `assets/*.svg` (4 visuels animés CSS)
- **Direction artistique** : `studio/` (bible, scénario, storyboard, manifest, credits)
- **Code** : `src/lulucode/` · **Tests** : `tests/` · **Outil agent** : `AGENTS.md`

## Arborescence commentée

```
pyproject.toml        Paquet `lulucode`, script `lulucode` → cli.main:app, extras terminal/web/dev
AGENTS.md             Règles d'or pour tout agent IA travaillant ici (niveau 3, zone, cœur/façades)
PROJECT_MAP.md        Ce fichier studio/
  bible.md            Palette, typo, langage animé, interdits — source de vérité visuelle
  scenario.md         Récit de la vitrine en 4 écrans
  storyboard.json     4 plans (source: code)
  manifest.json       Provenance/licence des assets (100 % maison)
  credits.md          Crédits publics assets/
  banner.svg          Bannière 1200×300 animée (cascade + curseur)
  terminal.svg        Session terminal 900×500 animée (cascade + curseur)
  architecture.svg    Schéma 1000×660 animé (couches + tirets de flux)
  permissions.svg     Schéma 1000×430 animé (balayage + stagger)
src/lulucode/
  __init__.py         __version__ = "0.1.0"
  core/
    events.py         Kind, Evenement, Collecteur — le contrat façades ↔ cœur
    agent.py          Agent (boucle), OUTILS (5 outils + schémas + niveaux), Plafonds
  model/
    client.py         Profil, ClientModele (httpx), charge_config/profil_actif,
                      ecrit_config_exemple, valide_appel
  permissions/
    moteur.py         Niveau 0-3, Mode, DecisionValeur, Moteur, resous_dans_zone
  tools/
    fichiers.py       lire/lister/chercher/ecrire + diff — tout passe par la zone
    commandes.py      lance_commande (subprocess, délai, sortie tronquée)
  cli/
    main.py           Façade terminal : run (option --profil, --mode), boucle,
                      _EmetteurTerminal, _permission_terminal ([o]/[s]/[n])
tests/                test_moteur, test_fichiers, test_agent (ModeleFictif, sans réseau)
```

## Modèle de données (essentiel)

- **Evenement** : `type: Kind` + `donnees: dict` + horodatage. Kind :
  tache_demarree, texte, outil_appel, outil_resultat, diff,
  permission_demandee, permission_reponse, erreur, plafond, tache_terminee.
- **Moteur.autoriser(outil, niveau, pour_la_session)** → Decision(valeur,
  niveau, raison). Invariants : strict ⇒ tout confirmé ; lecture-seule ⇒
  refuse ≥ écriture ; niveau 3 jamais mémorisé (`ValueError`).
- **Config TOML** `~/.config/lulucode/config.toml` : `[profils.X]`
  (base_url, model, api_key|api_key_env, contexte, outils_natifs),
  `[general]` (profil_par_defaut, plafond_etapes, plafond_tokens).
  Env : `LULUCODE_CONFIG`, `LULUCODE_PROFIL`.

## Flux principal

`Agent.execute(tache)` → boucle : `ClientModele.completions(messages,
outils)` → si appel d'outil : `valide_appel` → `Moteur.autoriser` →
si confirmation : callback façade `permission()` → exécution outil →
résultat en message `tool` → jusqu'à texte final ou plafond.

## Commandes

```bash
.venv\Scripts\activate
pip install -e ".[dev]"    # ruff/mypy indisponible sur Python 3.15 (voir AGENTS.md)
pytest
lulucode config init       # TODO: sous-commande à écrire (ecrit_config_exemple existe)
lulucode run --profil local --mode strict
```

## État v0.1.0 et suite

Fait : cœur, permissions, outils, client, CLI, tests.
Reste (README § Feuille de route) : `lulucode config init` (sous-commande),
façade web (FastAPI+React+SSE), DocScan, web, résumé de contexte, mode de
secours sans outils natifs, PyPI.
