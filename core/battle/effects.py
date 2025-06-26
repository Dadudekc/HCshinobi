"""Utilities for applying status effects."""
from __future__ import annotations

from typing import List

from .types import StatusEffect, BattleLogCallback
from .state import BattleState


def add_status_effect(state: BattleState, participant_id: str, effect: StatusEffect, log: BattleLogCallback) -> None:
    participant = state.attacker if state.attacker.id == participant_id else state.defender
    existing = next((e for e in participant.effects if e["name"] == effect.name), None)
    if existing:
        existing["duration"] = max(existing["duration"], effect.duration)
        existing["potency"] = max(existing.get("potency", 0), effect.potency)
        log(state, f"{participant.character.name} was refreshed by {effect.name}!")
    else:
        participant.effects.append(effect.to_dict())
        log(state, f"{participant.character.name} was affected by {effect.name}!")


def apply_status_effects(state: BattleState, trigger: str, log: BattleLogCallback) -> None:
    participant = state.attacker if state.current_turn_player_id == state.attacker.id else state.defender
    for eff_dict in list(participant.effects):
        effect = StatusEffect.from_dict(eff_dict)
        if effect.effect_type != trigger:
            continue
        if effect.name.lower() == "poison":
            dmg = int(participant.character.max_hp * effect.potency)
            participant.current_hp = max(participant.current_hp - dmg, 0)
            log(state, f"{participant.character.name} took {dmg} poison damage")
        elif effect.name.lower() == "regeneration":
            heal = int(participant.character.max_hp * effect.potency)
            participant.current_hp = min(participant.current_hp + heal, participant.character.max_hp)
            log(state, f"{participant.character.name} regenerated {heal} HP")


def tick_status_durations(state: BattleState, log: BattleLogCallback) -> None:
    for participant in (state.attacker, state.defender):
        for eff_dict in list(participant.effects):
            eff_dict["duration"] -= 1
            if eff_dict["duration"] <= 0:
                participant.effects.remove(eff_dict)
                log(state, f"{participant.character.name}'s {eff_dict['name']} wore off")


def can_player_act(state: BattleState, player_id: str, log: BattleLogCallback) -> bool:
    participant = state.attacker if state.attacker.id == player_id else state.defender
    for eff in participant.effects:
        if eff.get("name") == "Stun" and eff.get("duration", 0) > 0:
            log(state, f"{participant.character.name} is stunned and cannot act")
            return False
    return True
