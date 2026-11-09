"""Chargement des skills LuluCode au format Claude.

Un skill est un dossier contenant un `SKILL.md` avec frontmatter YAML
(`name`, `description` — les mêmes champs que Claude Code) et un corps
d'instructions. LuluCode découvre les skills dans trois niveaux de
priorité : projet (`.lulucode/skills/`), utilisateur (~/.lulucode/skills/)
et embarqués dans le paquet (futurs skills standard).

Le corps du skill n'est PAS envoyé d'office au modèle : seule la liste
« name — description » est exposée (économie de contexte, comme Claude),
et le corps entier n'entre dans la conversation que lorsque l'utilisateur
demande explicitement ce skill (`/skill nom-skill`) ou que la tâche lui
correspond clairement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_MOTIF_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_MOTIF_CHAMP = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)


@dataclass
class Skill:
    """Un skill découvert sur disque, au format Claude."""

    name: str
    description: str
    chemin: str
    corps: str = field(default="", repr=False)

    def resume(self) -> str:
        """Ligne de liste : name — description (pour l'injection au modèle)."""
        return f"- {self.name} : {self.description}"


def _analyse_frontmatter(texte: str) -> tuple[dict[str, str], str]:
    """Sépare frontmatter YAML minimal (clé: valeur par ligne) et corps."""
    correspondance = _MOTIF_FRONTMATTER.match(texte)
    if not correspondance:
        return {}, texte
    champs = dict(_MOTIF_CHAMP.findall(correspondance.group(1)))
    return champs, texte[correspondance.end():]


def _charge_skill(chemin: Path, nom_dossier: str) -> Skill | None:
    """Lit un SKILL.md ; renvoie None si invalide (pas de levée)."""
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError:
        return None
    champs, corps = _analyse_frontmatter(texte)
    name = (champs.get("name") or nom_dossier).strip()
    description = champs.get("description", "").strip()
    if not name or not description:
        # Sans name et description, le skill n'est pas exposé : même
        # règle que Claude (la description sert à décider du déclenchement).
        return None
    return Skill(name=name, description=description, chemin=str(chemin), corps=corps)


def decouvre_skills(dossier_projet: Path | None = None) -> list[Skill]:
    """Découvre les skills : projet, utilisateur, embarqué (par priorité).

    Un skill du projet masque celui de l'utilisateur qui porte le même
    nom (même règle que Claude Code).
    """
    racines: list[Path] = []
    if dossier_projet is not None:
        racines.append(Path(dossier_projet) / ".lulucode" / "skills")
    racines.append(Path.home() / ".lulucode" / "skills")

    trouves: dict[str, Skill] = {}
    for racine in racines:
        if not racine.is_dir():
            continue
        for dossier in sorted(racine.iterdir(), key=lambda p: p.name):
            if dossier.is_dir() or dossier.suffix == ".md":
                chemin = (dossier / "SKILL.md") if dossier.is_dir() else dossier
                nom_dossier = dossier.stem if dossier.is_dir() else dossier.stem
                skill = _charge_skill(chemin, nom_dossier)
                if skill is not None and skill.name not in trouves:
                    trouves[skill.name] = skill
    return sorted(trouves.values(), key=lambda s: s.name)


def liste_pour_modele(skills: list[Skill]) -> str:
    """Bloc injecté dans le system prompt quand des skills existent."""
    if not skills:
        return ""
    lignes = "\n".join(s.resume() for s in skills)
    return (
        "\n\n---\n# Skills disponibles\n\n"
        "L'utilisateur peut activer l'un de ces packs d'instructions "
        f"spécialisées avec `/skill nom` :\n\n{lignes}\n"
    ).strip()


def corps_du_skill(skills: list[Skill], nom: str) -> str | None:
    """Corps complet du skill demandé, None si absent."""
    for skill in skills:
        if skill.name == nom:
            if skill.corps:
                return skill.corps
            # Corps jamais lu (découverte par liste) : lecture au vol.
            try:
                return Path(skill.chemin).read_text(encoding="utf-8")
            except OSError:
                return None
    return None
