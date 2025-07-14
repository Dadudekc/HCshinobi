"""
Modern Mission System v2.0
Unified mission system with modern content and no legacy references.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

class MissionType(Enum):
    """Modern mission types."""
    ELIMINATION = "elimination"
    CAPTURE = "capture"
    ESCORT = "escort"
    DEFENSE = "defense"
    INFILTRATION = "infiltration"
    BOSS_BATTLE = "boss_battle"
    TRAINING = "training"
    INVESTIGATION = "investigation"

class MissionDifficulty(Enum):
    """Mission difficulty levels."""
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    S = "S"

class MissionStatus(Enum):
    """Mission status."""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class ModernMission:
    """Modern mission with unified content."""
    
    def __init__(self, 
                 mission_id: str,
                 name: str,
                 description: str,
                 mission_type: MissionType,
                 difficulty: MissionDifficulty,
                 village: str,
                 rewards: Dict[str, Any],
                 duration: timedelta,
                 requirements: Optional[Dict[str, Any]] = None):
        
        self.mission_id = mission_id
        self.name = name
        self.description = description
        self.mission_type = mission_type
        self.difficulty = difficulty
        self.village = village
        self.rewards = rewards
        self.duration = duration
        self.requirements = requirements or {}
        self.status = MissionStatus.AVAILABLE
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Mission progress tracking
        self.objectives: List[str] = []
        self.completed_objectives: List[str] = []
        self.participants: List[Dict[str, Any]] = []
        self.battle_log: List[Dict[str, Any]] = []
        
    def start_mission(self, participants: List[Dict[str, Any]]) -> bool:
        """Start the mission with participants."""
        if self.status != MissionStatus.AVAILABLE:
            return False
        
        self.participants = participants
        self.status = MissionStatus.ACTIVE
        self.started_at = datetime.now()
        
        # Generate mission-specific objectives
        self.objectives = self._generate_objectives()
        
        return True
    
    def _generate_objectives(self) -> List[str]:
        """Generate mission-specific objectives."""
        objectives = []
        
        if self.mission_type == MissionType.ELIMINATION:
            objectives.append(f"Defeat all enemies")
            if self.difficulty in [MissionDifficulty.B, MissionDifficulty.A, MissionDifficulty.S]:
                objectives.append("Survive the encounter")
        
        elif self.mission_type == MissionType.CAPTURE:
            objectives.append("Capture the target alive")
            objectives.append("Return target to village")
        
        elif self.mission_type == MissionType.ESCORT:
            objectives.append("Protect the client")
            objectives.append("Reach the destination")
        
        elif self.mission_type == MissionType.DEFENSE:
            objectives.append("Defend the location")
            objectives.append("Prevent enemy infiltration")
        
        elif self.mission_type == MissionType.INFILTRATION:
            objectives.append("Infiltrate enemy territory")
            objectives.append("Gather intelligence")
            objectives.append("Return undetected")
        
        elif self.mission_type == MissionType.BOSS_BATTLE:
            objectives.append("Defeat the boss")
            objectives.append("Survive the encounter")
        
        elif self.mission_type == MissionType.TRAINING:
            objectives.append("Complete training exercises")
            objectives.append("Improve skills")
        
        elif self.mission_type == MissionType.INVESTIGATION:
            objectives.append("Investigate the area")
            objectives.append("Find clues")
            objectives.append("Report findings")
        
        return objectives
    
    def complete_objective(self, objective: str) -> bool:
        """Mark an objective as completed."""
        if objective in self.objectives and objective not in self.completed_objectives:
            self.completed_objectives.append(objective)
            return True
        return False
    
    def check_completion(self) -> bool:
        """Check if all objectives are completed."""
        return len(self.completed_objectives) >= len(self.objectives)
    
    def complete_mission(self, success: bool = True) -> Dict[str, Any]:
        """Complete the mission and return rewards."""
        self.status = MissionStatus.COMPLETED if success else MissionStatus.FAILED
        self.completed_at = datetime.now()
        
        if success and self.check_completion():
            return self.rewards
        else:
            # Return partial rewards for failed missions
            partial_rewards = {}
            for key, value in self.rewards.items():
                if isinstance(value, (int, float)):
                    partial_rewards[key] = int(value * 0.3)  # 30% of rewards
                else:
                    partial_rewards[key] = value
            return partial_rewards
    
    def add_battle_log_entry(self, entry: Dict[str, Any]) -> None:
        """Add an entry to the battle log."""
        entry["timestamp"] = datetime.now().isoformat()
        entry["turn"] = len(self.battle_log) + 1
        self.battle_log.append(entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mission to dictionary."""
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "description": self.description,
            "mission_type": self.mission_type.value,
            "difficulty": self.difficulty.value,
            "village": self.village,
            "rewards": self.rewards,
            "duration": str(self.duration),
            "requirements": self.requirements,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "objectives": self.objectives,
            "completed_objectives": self.completed_objectives,
            "participants": self.participants,
            "battle_log": self.battle_log
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModernMission":
        """Create mission from dictionary."""
        mission = cls(
            mission_id=data["mission_id"],
            name=data["name"],
            description=data["description"],
            mission_type=MissionType(data["mission_type"]),
            difficulty=MissionDifficulty(data["difficulty"]),
            village=data["village"],
            rewards=data["rewards"],
            duration=timedelta.fromisoformat(data["duration"]),
            requirements=data.get("requirements", {})
        )
        
        mission.status = MissionStatus(data["status"])
        mission.created_at = datetime.fromisoformat(data["created_at"])
        
        if data.get("started_at"):
            mission.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            mission.completed_at = datetime.fromisoformat(data["completed_at"])
        
        mission.objectives = data.get("objectives", [])
        mission.completed_objectives = data.get("completed_objectives", [])
        mission.participants = data.get("participants", [])
        mission.battle_log = data.get("battle_log", [])
        
        return mission

class ModernMissionGenerator:
    """Generator for modern missions."""
    
    def __init__(self):
        self.mission_templates = self._load_mission_templates()
        self.villages = ["Konohagakure", "Sunagakure", "Kirigakure", "Kumogakure", "Iwagakure"]
    
    def _load_mission_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load mission templates."""
        return {
            "elimination": [
                {
                    "name": "Bandit Hunt",
                    "description": "Eliminate bandits threatening the village outskirts.",
                    "difficulty": MissionDifficulty.D,
                    "rewards": {"exp": 50, "ryo": 100}
                },
                {
                    "name": "Missing-nin Elimination",
                    "description": "Track down and eliminate a rogue shinobi.",
                    "difficulty": MissionDifficulty.C,
                    "rewards": {"exp": 100, "ryo": 200}
                },
                {
                    "name": "Elite Target Elimination",
                    "description": "Take down a high-ranking enemy shinobi.",
                    "difficulty": MissionDifficulty.B,
                    "rewards": {"exp": 200, "ryo": 400}
                }
            ],
            "capture": [
                {
                    "name": "Criminal Capture",
                    "description": "Capture a wanted criminal alive.",
                    "difficulty": MissionDifficulty.C,
                    "rewards": {"exp": 150, "ryo": 300}
                },
                {
                    "name": "Spy Capture",
                    "description": "Capture an enemy spy for interrogation.",
                    "difficulty": MissionDifficulty.B,
                    "rewards": {"exp": 250, "ryo": 500}
                }
            ],
            "escort": [
                {
                    "name": "Merchant Escort",
                    "description": "Protect a merchant caravan from bandits.",
                    "difficulty": MissionDifficulty.C,
                    "rewards": {"exp": 75, "ryo": 150}
                },
                {
                    "name": "VIP Escort",
                    "description": "Escort an important person to safety.",
                    "difficulty": MissionDifficulty.B,
                    "rewards": {"exp": 200, "ryo": 400}
                }
            ],
            "defense": [
                {
                    "name": "Village Defense",
                    "description": "Defend the village from enemy attack.",
                    "difficulty": MissionDifficulty.A,
                    "rewards": {"exp": 300, "ryo": 600}
                },
                {
                    "name": "Border Defense",
                    "description": "Defend the village border from infiltration.",
                    "difficulty": MissionDifficulty.B,
                    "rewards": {"exp": 200, "ryo": 400}
                }
            ],
            "infiltration": [
                {
                    "name": "Enemy Territory Infiltration",
                    "description": "Infiltrate enemy territory to gather intelligence.",
                    "difficulty": MissionDifficulty.A,
                    "rewards": {"exp": 300, "ryo": 600}
                },
                {
                    "name": "Stealth Mission",
                    "description": "Complete a mission without being detected.",
                    "difficulty": MissionDifficulty.B,
                    "rewards": {"exp": 200, "ryo": 400}
                }
            ],
            "boss_battle": [
                {
                    "name": "Legendary Shinobi Battle",
                    "description": "Face off against a legendary shinobi.",
                    "difficulty": MissionDifficulty.S,
                    "rewards": {"exp": 500, "ryo": 1000, "tokens": 50}
                }
            ],
            "training": [
                {
                    "name": "Advanced Training",
                    "description": "Complete advanced training exercises.",
                    "difficulty": MissionDifficulty.D,
                    "rewards": {"exp": 30, "ryo": 50}
                },
                {
                    "name": "Elite Training",
                    "description": "Undergo elite training to improve skills.",
                    "difficulty": MissionDifficulty.C,
                    "rewards": {"exp": 75, "ryo": 150}
                }
            ],
            "investigation": [
                {
                    "name": "Mystery Investigation",
                    "description": "Investigate mysterious events in the area.",
                    "difficulty": MissionDifficulty.C,
                    "rewards": {"exp": 100, "ryo": 200}
                },
                {
                    "name": "Criminal Investigation",
                    "description": "Investigate criminal activities.",
                    "difficulty": MissionDifficulty.B,
                    "rewards": {"exp": 150, "ryo": 300}
                }
            ]
        }
    
    def generate_mission(self, 
                        mission_type: MissionType,
                        difficulty: MissionDifficulty,
                        village: Optional[str] = None) -> ModernMission:
        """Generate a new mission."""
        import uuid
        
        # Get templates for the mission type
        templates = self.mission_templates.get(mission_type.value, [])
        if not templates:
            # Fallback to elimination if type not found
            templates = self.mission_templates["elimination"]
        
        # Filter by difficulty
        available_templates = [t for t in templates if t["difficulty"] == difficulty]
        if not available_templates:
            # Use first available template
            available_templates = templates
        
        # Select random template
        template = random.choice(available_templates)
        
        # Generate mission ID
        mission_id = f"{mission_type.value}_{difficulty.value}_{uuid.uuid4().hex[:8]}"
        
        # Select village
        if not village:
            village = random.choice(self.villages)
        
        # Calculate duration based on difficulty
        duration_hours = {
            MissionDifficulty.D: 1,
            MissionDifficulty.C: 2,
            MissionDifficulty.B: 4,
            MissionDifficulty.A: 6,
            MissionDifficulty.S: 8
        }
        duration = timedelta(hours=duration_hours[difficulty])
        
        # Generate requirements
        requirements = self._generate_requirements(difficulty)
        
        return ModernMission(
            mission_id=mission_id,
            name=template["name"],
            description=template["description"],
            mission_type=mission_type,
            difficulty=difficulty,
            village=village,
            rewards=template["rewards"],
            duration=duration,
            requirements=requirements
        )
    
    def _generate_requirements(self, difficulty: MissionDifficulty) -> Dict[str, Any]:
        """Generate mission requirements based on difficulty."""
        requirements = {}
        
        if difficulty == MissionDifficulty.D:
            requirements["min_level"] = 1
        elif difficulty == MissionDifficulty.C:
            requirements["min_level"] = 5
        elif difficulty == MissionDifficulty.B:
            requirements["min_level"] = 10
        elif difficulty == MissionDifficulty.A:
            requirements["min_level"] = 20
        elif difficulty == MissionDifficulty.S:
            requirements["min_level"] = 30
        
        return requirements

class ModernMissionSystem:
    """Modern mission system manager."""
    
    def __init__(self):
        self.generator = ModernMissionGenerator()
        self.active_missions: Dict[str, ModernMission] = {}
        self.completed_missions: Dict[str, ModernMission] = {}
        self.data_dir = Path("data/missions")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def create_mission(self, 
                      mission_type: MissionType,
                      difficulty: MissionDifficulty,
                      village: Optional[str] = None) -> ModernMission:
        """Create a new mission."""
        mission = self.generator.generate_mission(mission_type, difficulty, village)
        return mission
    
    def start_mission(self, mission: ModernMission, participants: List[Dict[str, Any]]) -> bool:
        """Start a mission."""
        if mission.start_mission(participants):
            self.active_missions[mission.mission_id] = mission
            return True
        return False
    
    def complete_mission(self, mission_id: str, success: bool = True) -> Optional[Dict[str, Any]]:
        """Complete a mission and return rewards."""
        if mission_id not in self.active_missions:
            return None
        
        mission = self.active_missions[mission_id]
        rewards = mission.complete_mission(success)
        
        # Move to completed missions
        self.completed_missions[mission_id] = mission
        del self.active_missions[mission_id]
        
        return rewards
    
    def get_active_missions(self) -> List[ModernMission]:
        """Get all active missions."""
        return list(self.active_missions.values())
    
    def get_completed_missions(self) -> List[ModernMission]:
        """Get all completed missions."""
        return list(self.completed_missions.values())
    
    def get_mission(self, mission_id: str) -> Optional[ModernMission]:
        """Get a specific mission."""
        return self.active_missions.get(mission_id) or self.completed_missions.get(mission_id)
    
    def save_missions(self) -> None:
        """Save missions to disk."""
        # Save active missions
        active_missions_data = {
            mission_id: mission.to_dict() 
            for mission_id, mission in self.active_missions.items()
        }
        
        with open(self.data_dir / "active_missions.json", 'w', encoding='utf-8') as f:
            json.dump(active_missions_data, f, indent=2, ensure_ascii=False)
        
        # Save completed missions
        completed_missions_data = {
            mission_id: mission.to_dict() 
            for mission_id, mission in self.completed_missions.items()
        }
        
        with open(self.data_dir / "completed_missions.json", 'w', encoding='utf-8') as f:
            json.dump(completed_missions_data, f, indent=2, ensure_ascii=False)
    
    def load_missions(self) -> None:
        """Load missions from disk."""
        # Load active missions
        active_file = self.data_dir / "active_missions.json"
        if active_file.exists():
            with open(active_file, 'r', encoding='utf-8') as f:
                active_data = json.load(f)
            
            for mission_id, mission_data in active_data.items():
                mission = ModernMission.from_dict(mission_data)
                self.active_missions[mission_id] = mission
        
        # Load completed missions
        completed_file = self.data_dir / "completed_missions.json"
        if completed_file.exists():
            with open(completed_file, 'r', encoding='utf-8') as f:
                completed_data = json.load(f)
            
            for mission_id, mission_data in completed_data.items():
                mission = ModernMission.from_dict(mission_data)
                self.completed_missions[mission_id] = mission 