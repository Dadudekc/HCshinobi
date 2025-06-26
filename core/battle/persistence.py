"""Save and load battle states to JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict
from datetime import datetime, timezone

from .state import BattleState, BattleParticipant
from .types import StatusEffect
from ..character import Character


class BattlePersistence:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir) / "battles"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.active_file = self.data_dir / "active_battles.json"
        self.history_file = self.data_dir / "battle_history.json"
        self.active_battles: Dict[str, BattleState] = {}

    async def add_active_battle(self, battle_id: str, state: BattleState) -> None:
        self.active_battles[battle_id] = state
        await self.save_active_battles()

    async def remove_active_battle(self, battle_id: str) -> None:
        self.active_battles.pop(battle_id, None)
        await self.save_active_battles()

    async def add_battle_to_history(self, battle_id: str, state: BattleState) -> None:
        history = await self.load_battle_history()
        history.setdefault(battle_id, []).extend(state.battle_log)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    async def save_active_battles(self) -> None:
        data = {bid: self._state_to_dict(b) for bid, b in self.active_battles.items()}
        with open(self.active_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def load_active_battles(self) -> Dict[str, BattleState]:
        if not self.active_file.exists():
            return {}
        with open(self.active_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        battles = {bid: self._state_from_dict(b) for bid, b in raw.items()}
        self.active_battles = battles
        return battles

    async def load_battle_history(self) -> Dict[str, list]:
        if not self.history_file.exists():
            return {}
        with open(self.history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _state_to_dict(self, state: BattleState) -> Dict:
        return {
            "attacker": self._participant_to_dict(state.attacker),
            "defender": self._participant_to_dict(state.defender),
            "current_turn_player_id": state.current_turn_player_id,
            "id": state.id,
            "turn_number": state.turn_number,
            "battle_log": state.battle_log,
            "winner_id": state.winner_id,
            "last_action": state.last_action.isoformat(),
            "is_active": state.is_active,
            "end_reason": state.end_reason,
        }

    def _state_from_dict(self, data: Dict) -> BattleState:
        attacker = self._participant_from_dict(data["attacker"])
        defender = self._participant_from_dict(data["defender"])
        state = BattleState(
            attacker=attacker,
            defender=defender,
            current_turn_player_id=data["current_turn_player_id"],
            id=data.get("id", ""),
            turn_number=data.get("turn_number", 1),
            battle_log=data.get("battle_log", []),
        )
        state.winner_id = data.get("winner_id")
        state.last_action = (
            datetime.fromisoformat(data["last_action"]) if "last_action" in data else datetime.now(timezone.utc)
        )
        state.is_active = data.get("is_active", True)
        state.end_reason = data.get("end_reason")
        return state

    def _participant_to_dict(self, p: BattleParticipant) -> Dict:
        return {
            "character": p.character.to_dict(),
            "current_hp": p.current_hp,
            "effects": p.effects,
        }

    def _participant_from_dict(self, data: Dict) -> BattleParticipant:
        char = Character.from_dict(data["character"])
        participant = BattleParticipant.from_character(char)
        participant.current_hp = data.get("current_hp", char.hp)
        participant.effects = data.get("effects", [])
        return participant
