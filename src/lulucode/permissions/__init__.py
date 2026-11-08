"""Permissions de LuluCode : la pièce centrale.

Aucune action n'est exécutée sans qu'une règle l'ait autorisée. Les actions
de niveau 3 ne peuvent jamais être autorisées pour toute la session.
"""

from lulucode.permissions.moteur import Decision, DecisionValeur, Moteur, Mode, Niveau

__all__ = ["Decision", "DecisionValeur", "Moteur", "Mode", "Niveau"]
