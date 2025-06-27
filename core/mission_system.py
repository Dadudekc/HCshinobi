"""Very small mission system for tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .currency_system import CurrencySystem
from .progression_engine import ShinobiProgressionEngine


class MissionSystem:
    def __init__(
        self,
        data_dir: str = "data",
        currency_system: Optional[CurrencySystem] = None,
        progression_engine: Optional[ShinobiProgressionEngine] = None,
    ) -> None:
        self.data_dir = Path(data_dir) / "missions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.def_file = self.data_dir / "mission_definitions.json"
        self.active_file = self.data_dir / "active_missions.json"
        self.completed_file = self.data_dir / "completed_missions.json"
        self.currency_system = currency_system
        self.progression_engine = progression_engine
        self._load_definitions()
        self.active: Dict[str, Dict] = {}
        self.completed: Dict[str, List[Dict]] = {}

    def _load_definitions(self) -> None:
        self.definitions = []
        if self.def_file.exists():
            with open(self.def_file, "r", encoding="utf-8") as f:
                self.definitions = json.load(f)

    async def get_available_missions(self, player_id: str) -> List[Dict]:
        return self.definitions

    async def assign_mission(self, player_id: str, mission_id: str) -> Tuple[bool, str]:
        mission = next((m for m in self.definitions if m.get("mission_id") == mission_id), None)
        if not mission:
            return False, "Mission not found"
        self.active[player_id] = mission
        return True, f"Mission '{mission_id}' accepted!"

    async def get_active_mission(self, player_id: str) -> Dict | None:
        return self.active.get(player_id)

    async def complete_mission(self, player_id: str) -> Tuple[bool, str, Dict]:
        mission = self.active.pop(player_id, None)
        if not mission:
            return False, "No active mission", {}
        self.completed.setdefault(player_id, []).append(mission)

        rewards = {
            "exp": mission.get("reward_exp", 0),
            "ryo": mission.get("reward_ryo", 0),
            "items": []
        }

        if self.currency_system and rewards["ryo"]:
            self.currency_system.add_balance_and_save(player_id, rewards["ryo"])

        if self.progression_engine and rewards["exp"]:
            await self.progression_engine.award_mission_experience(player_id, rewards["exp"])

        return True, "Mission completed successfully", rewards
