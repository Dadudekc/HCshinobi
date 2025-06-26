from typing import List
from .state import BattleState
from .types import StatusEffect, BattleLogCallback


def _get_participant(battle: BattleState, pid: str):
    if battle.attacker.id == pid:
        return battle.attacker
    return battle.defender


def add_status_effect(battle: BattleState, participant_id: str, effect: StatusEffect, log: BattleLogCallback) -> None:
    participant = _get_participant(battle, participant_id)
    for existing in participant.effects:
        if existing["name"] == effect.name:
            existing["duration"] = max(existing["duration"], effect.duration)
            existing["potency"] = max(existing["potency"], effect.potency)
            log(battle, f"{participant.character.name} was refreshed with {effect.name}")
            return
    participant.effects.append(effect.to_dict())
    log(battle, f"{participant.character.name} was affected by {effect.name}")


def apply_status_effects(battle: BattleState, effect_type: str, log: BattleLogCallback) -> None:
    for participant in [battle.attacker, battle.defender]:
        for eff in list(participant.effects):
            if eff["effect_type"] != effect_type:
                continue
            if eff["name"] == "Poison":
                dmg = int(participant.character.max_hp * eff["potency"])
                participant.current_hp -= dmg
                log(battle, f"{participant.character.name} took {dmg} poison damage")
            if eff["name"] == "Regeneration":
                heal = int(participant.character.max_hp * eff["potency"])
                participant.current_hp = min(participant.character.max_hp, participant.current_hp + heal)
                log(battle, f"{participant.character.name} regenerated {heal} HP")


def tick_status_durations(battle: BattleState, log: BattleLogCallback) -> None:
    for participant in [battle.attacker, battle.defender]:
        remaining = []
        for eff in participant.effects:
            eff["duration"] -= 1
            if eff["duration"] <= 0:
                log(battle, f"{eff['name']} on {participant.character.name} wore off")
            else:
                remaining.append(eff)
        participant.effects = remaining


def can_player_act(battle: BattleState, participant_id: str, log: BattleLogCallback) -> bool:
    participant = _get_participant(battle, participant_id)
    for eff in participant.effects:
        if eff["name"] == "Stun" and eff["duration"] > 0:
            log(battle, f"{participant.character.name} is stunned and cannot act")
            return False
    return True
