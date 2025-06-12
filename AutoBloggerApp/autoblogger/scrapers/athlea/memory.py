from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import json
from pathlib import Path


@dataclass
class Quest:
    id: str
    title: str
    type: str  # blocker, feature, refactor, etc.
    resolved: bool
    summary: str
    xp_gained: int = 0
    lore_items: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Memory:
    level: int
    faction: str
    quests: List[Quest] = field(default_factory=list)
    breakthroughs: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_json(self) -> Dict:
        """Convert memory to JSON-serializable dict"""
        return {
            "level": self.level,
            "faction": self.faction,
            "quests": [
                {
                    "id": q.id,
                    "title": q.title,
                    "type": q.type,
                    "resolved": q.resolved,
                    "summary": q.summary,
                    "xp_gained": q.xp_gained,
                    "lore_items": q.lore_items,
                    "timestamp": q.timestamp.isoformat(),
                }
                for q in self.quests
            ],
            "breakthroughs": self.breakthroughs,
            "blockers": self.blockers,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, data: Dict) -> "Memory":
        """Create Memory instance from JSON data"""
        quests = [
            Quest(
                id=q["id"],
                title=q["title"],
                type=q["type"],
                resolved=q["resolved"],
                summary=q["summary"],
                xp_gained=q.get("xp_gained", 0),
                lore_items=q.get("lore_items", []),
                timestamp=datetime.fromisoformat(q["timestamp"]),
            )
            for q in data["quests"]
        ]

        return cls(
            level=data["level"],
            faction=data["faction"],
            quests=quests,
            breakthroughs=data["breakthroughs"],
            blockers=data["blockers"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class MemoryBank:
    def __init__(self, base_path: str = "memory_bank"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def save_memory(self, memory: Memory, filename: Optional[str] = None) -> bool:
        """Save memory to JSON file"""
        try:
            if filename is None:
                filename = f"memory_{memory.timestamp.strftime('%Y%m%d_%H%M%S')}.json"

            filepath = self.base_path / filename
            with open(filepath, "w") as f:
                json.dump(memory.to_json(), f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save memory: {str(e)}")
            return False

    def load_memory(self, filename: str) -> Optional[Memory]:
        """Load memory from JSON file"""
        try:
            filepath = self.base_path / filename
            with open(filepath, "r") as f:
                data = json.load(f)
            return Memory.from_json(data)
        except Exception as e:
            print(f"Failed to load memory: {str(e)}")
            return None

    def list_memories(self) -> List[str]:
        """List all memory files"""
        return [f.name for f in self.base_path.glob("*.json")]
