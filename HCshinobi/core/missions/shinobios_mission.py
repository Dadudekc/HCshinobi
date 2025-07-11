"""
ShinobiOS Mission Integration
Extends the base Mission system with immersive battle simulation
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from enum import Enum
import random

from .mission import Mission, MissionStatus, MissionDifficulty
from .shinobios_engine import ShinobiOSEngine, ShinobiStats, BattleAction, EnvironmentEffect

class BattleMissionType(Enum):
    ELIMINATION = "elimination"
    CAPTURE = "capture"
    ESCORT = "escort"
    DEFENSE = "defense"
    INFILTRATION = "infiltration"
    BOSS_BATTLE = "boss_battle"

@dataclass
class BattleParticipant:
    """Participant in a battle mission"""
    user_id: str
    name: str
    stats: ShinobiStats
    is_player: bool = True
    status: str = "active"  # active, defeated, escaped
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "stats": {
                "chakra": self.stats.chakra,
                "max_chakra": self.stats.max_chakra,
                "health": self.stats.health,
                "max_health": self.stats.max_health,
                "stamina": self.stats.stamina,
                "max_stamina": self.stats.max_stamina,
                "level": self.stats.level,
                "experience": self.stats.experience
            },
            "is_player": self.is_player,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], engine: ShinobiOSEngine) -> "BattleParticipant":
        stats_data = data.get("stats", {})
        stats = ShinobiStats(
            chakra=stats_data.get("chakra", 100),
            max_chakra=stats_data.get("max_chakra", 100),
            health=stats_data.get("health", 100),
            max_health=stats_data.get("max_health", 100),
            stamina=stats_data.get("stamina", 100),
            max_stamina=stats_data.get("max_stamina", 100),
            level=stats_data.get("level", 1),
            experience=stats_data.get("experience", 0)
        )
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            stats=stats,
            is_player=data.get("is_player", True),
            status=data.get("status", "active")
        )

@dataclass
class BattleState:
    """Current state of a battle mission"""
    participants: List[BattleParticipant] = field(default_factory=list)
    current_turn: int = 0
    battle_log: List[Dict[str, Any]] = field(default_factory=list)
    environment: Optional[EnvironmentEffect] = None
    objectives: List[str] = field(default_factory=list)
    completed_objectives: List[str] = field(default_factory=list)
    
    def add_participant(self, participant: BattleParticipant) -> None:
        self.participants.append(participant)
    
    def get_active_participants(self) -> List[BattleParticipant]:
        return [p for p in self.participants if p.status == "active"]
    
    def get_players(self) -> List[BattleParticipant]:
        return [p for p in self.participants if p.is_player and p.status == "active"]
    
    def get_enemies(self) -> List[BattleParticipant]:
        return [p for p in self.participants if not p.is_player and p.status == "active"]
    
    def add_battle_log(self, action: BattleAction) -> None:
        self.battle_log.append({
            "turn": self.current_turn,
            "actor": action.actor,
            "target": action.target,
            "jutsu": action.jutsu.name,
            "success": action.success,
            "damage": action.damage,
            "narration": action.narration,
            "timestamp": action.timestamp.isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "participants": [p.to_dict() for p in self.participants],
            "current_turn": self.current_turn,
            "battle_log": self.battle_log,
            "environment": self.environment.name if self.environment else None,
            "objectives": self.objectives,
            "completed_objectives": self.completed_objectives
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], engine: ShinobiOSEngine) -> "BattleState":
        participants = [BattleParticipant.from_dict(p, engine) for p in data.get("participants", [])]
        environment = None
        if data.get("environment"):
            environment = engine.environments.get(data["environment"])
        
        return cls(
            participants=participants,
            current_turn=data.get("current_turn", 0),
            battle_log=data.get("battle_log", []),
            environment=environment,
            objectives=data.get("objectives", []),
            completed_objectives=data.get("completed_objectives", [])
        )

class ShinobiOSMission(Mission):
    """Mission with ShinobiOS battle simulation capabilities"""
    
    def __init__(self, engine: ShinobiOSEngine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.battle_state: Optional[BattleState] = None
        self.mission_type: BattleMissionType = BattleMissionType.ELIMINATION
        self.battle_id: str = str(uuid.uuid4())
        
    def initialize_battle(self, players: List[Dict[str, Any]], 
                         environment: str = "forest") -> None:
        """Initialize the battle with players and environment"""
        self.battle_state = BattleState()
        
        # Add players
        for player_data in players:
            player_stats = self.engine.create_shinobi(
                name=player_data["name"],
                level=player_data.get("level", 1),
                **player_data.get("stats", {})
            )
            participant = BattleParticipant(
                user_id=player_data["user_id"],
                name=player_data["name"],
                stats=player_stats,
                is_player=True
            )
            self.battle_state.add_participant(participant)
        
        # Create enemies based on mission difficulty
        diff = self.difficulty.value if hasattr(self.difficulty, 'value') else self.difficulty
        scenario = self.engine.create_mission_scenario(
            diff, 
            environment
        )
        
        for i, enemy_stats in enumerate(scenario["enemies"]):
            enemy_stats.name = f"Enemy {i+1}"
            participant = BattleParticipant(
                user_id=f"enemy_{i+1}",
                name=enemy_stats.name,
                stats=enemy_stats,
                is_player=False
            )
            self.battle_state.add_participant(participant)
        
        # Set environment and objectives
        self.battle_state.environment = scenario["environment"]
        self.battle_state.objectives = scenario["objectives"]
    
    async def execute_player_action(self, player_id: str, jutsu_name: str, 
                                   target_id: str) -> Dict[str, Any]:
        """Execute a player's action in the battle"""
        if not self.battle_state:
            raise ValueError("Battle not initialized")
        
        # Find player and target
        player = next((p for p in self.battle_state.participants 
                      if p.user_id == player_id and p.is_player), None)
        target = next((p for p in self.battle_state.participants 
                      if p.user_id == target_id), None)
        
        if not player or not target:
            return {"success": False, "error": "Invalid player or target"}
        
        # Get available jutsu
        available_jutsu = self.engine.get_available_jutsu(player.stats)
        jutsu = next((j for j in available_jutsu if j.name.lower() == jutsu_name.lower()), None)
        
        if not jutsu:
            return {"success": False, "error": "Jutsu not available"}
        
        # Execute action
        action = self.engine.execute_action(
            player.stats, 
            target.stats, 
            jutsu, 
            self.battle_state.environment
        )
        
        # Update battle state
        self.battle_state.current_turn += 1
        self.battle_state.add_battle_log(action)
        
        # Check if target is defeated
        if target.stats.health <= 0:
            target.status = "defeated"
        
        # Regenerate stats for all participants
        for participant in self.battle_state.get_active_participants():
            self.engine.regenerate_stats(participant.stats, self.battle_state.environment)
        
        # Check mission completion
        completion_status = self._check_mission_completion()
        
        return {
            "success": True,
            "action": {
                "actor": action.actor,
                "target": action.target,
                "jutsu": action.jutsu.name,
                "success": action.success,
                "damage": action.damage,
                "narration": action.narration
            },
            "battle_state": self.battle_state.to_dict(),
            "completion_status": completion_status
        }
    
    async def execute_enemy_turn(self) -> List[Dict[str, Any]]:
        """Execute enemy AI turns"""
        if not self.battle_state:
            return []
        
        actions = []
        enemies = self.battle_state.get_enemies()
        players = self.battle_state.get_players()
        
        for enemy in enemies:
            if enemy.stats.health <= 0:
                continue
            
            # Simple AI: attack random player
            if players:
                target = random.choice(players)
                available_jutsu = self.engine.get_available_jutsu(enemy.stats)
                
                if available_jutsu:
                    jutsu = random.choice(available_jutsu)
                    action = self.engine.execute_action(
                        enemy.stats,
                        target.stats,
                        jutsu,
                        self.battle_state.environment
                    )
                    
                    self.battle_state.add_battle_log(action)
                    actions.append({
                        "actor": action.actor,
                        "target": action.target,
                        "jutsu": action.jutsu.name,
                        "success": action.success,
                        "damage": action.damage,
                        "narration": action.narration
                    })
                    
                    # Check if target is defeated
                    if target.stats.health <= 0:
                        target.status = "defeated"
        
        # Regenerate stats
        for participant in self.battle_state.get_active_participants():
            self.engine.regenerate_stats(participant.stats, self.battle_state.environment)
        
        return actions
    
    def _check_mission_completion(self) -> Dict[str, Any]:
        """Check if mission objectives are completed"""
        if not self.battle_state:
            return {"completed": False, "status": "battle_not_initialized"}
        
        players = self.battle_state.get_players()
        enemies = self.battle_state.get_enemies()
        
        # Check for mission failure (all players defeated)
        if not players:
            return {
                "completed": True,
                "status": "failed",
                "reason": "All players defeated"
            }
        
        # Check for mission success (all enemies defeated)
        if not enemies:
            return {
                "completed": True,
                "status": "success",
                "reason": "All enemies defeated"
            }
        
        return {"completed": False, "status": "in_progress"}
    
    def get_battle_status(self) -> Dict[str, Any]:
        """Get current battle status"""
        if not self.battle_state:
            return {"error": "Battle not initialized"}
        
        return {
            "battle_id": self.battle_id,
            "mission_id": self.id,
            "current_turn": self.battle_state.current_turn,
            "participants": [p.to_dict() for p in self.battle_state.participants],
            "objectives": self.battle_state.objectives,
            "completed_objectives": self.battle_state.completed_objectives,
            "environment": self.battle_state.environment.name if self.battle_state.environment else None,
            "recent_actions": self.battle_state.battle_log[-5:] if self.battle_state.battle_log else []
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mission to dictionary with battle state"""
        base_dict = super().to_dict()
        base_dict.update({
            "battle_id": self.battle_id,
            "mission_type": self.mission_type.value,
            "battle_state": self.battle_state.to_dict() if self.battle_state else None
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], engine: ShinobiOSEngine) -> "ShinobiOSMission":
        """Create mission from dictionary"""
        # Accept both enum and string for difficulty
        diff = data.get("difficulty", "D")
        if not isinstance(diff, str):
            diff = diff.value
        mission = cls(
            engine=engine,
            id=data["id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            difficulty=diff,
            village=data.get("village", ""),
            reward=data.get("reward", {}),
            duration=timedelta(seconds=data.get("duration_seconds", 0)),
            requirements=data.get("requirements", {})
        )
        mission.battle_id = data.get("battle_id", str(uuid.uuid4()))
        mission.mission_type = BattleMissionType(data.get("mission_type", "elimination"))
        if data.get("battle_state"):
            mission.battle_state = BattleState.from_dict(data["battle_state"], engine)
        return mission 