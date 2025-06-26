"""Placeholder effects."""
from .types import StatusEffect, BattleLogCallback


async def apply_effect(effect: StatusEffect, callback: BattleLogCallback) -> None:
    callback(f"Applied effect: {effect.name}")
