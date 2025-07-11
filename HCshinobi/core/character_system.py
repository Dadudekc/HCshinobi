import json
import os
from typing import Dict, Optional
from .character import Character
from .constants import DATA_DIR, CHARACTERS_SUBDIR

class CharacterSystem:
    def __init__(self) -> None:
        self.characters: Dict[str, Character] = {}
        self.characters_dir = os.path.join(DATA_DIR, CHARACTERS_SUBDIR)
        os.makedirs(self.characters_dir, exist_ok=True)
        self._load_existing_characters()

    def _load_existing_characters(self) -> None:
        """Load all existing character files into memory on startup."""
        try:
            for filename in os.listdir(self.characters_dir):
                if filename.endswith('.json') and filename.replace('.json', '').isdigit():
                    user_id = filename.replace('.json', '')
                    character_data = self._load_character_from_file(user_id)
                    if character_data:
                        char = self._dict_to_character(character_data)
                        self.characters[user_id] = char
                        print(f"✅ Loaded character for user {user_id}: {char.name}")
        except Exception as e:
            print(f"Warning: Error loading existing characters: {e}")

    def _load_character_from_file(self, user_id: str) -> Optional[Dict]:
        """Load character data from JSON file."""
        try:
            character_file = os.path.join(self.characters_dir, f"{user_id}.json")
            with open(character_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading character file for {user_id}: {e}")
            return None

    def _save_character_to_file(self, character: Character) -> None:
        """Save character data to JSON file."""
        try:
            character_file = os.path.join(self.characters_dir, f"{character.id}.json")
            character_data = self._character_to_dict(character)
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving character file for {character.id}: {e}")

    def _character_to_dict(self, character: Character) -> Dict:
        """Convert Character object to dictionary for JSON serialization."""
        return {
            "id": character.id,
            "name": character.name,
            "clan": character.clan,
            "level": character.level,
            "rank": character.rank,
            "hp": character.hp,
            "max_hp": character.max_hp,
            "chakra": character.chakra,
            "max_chakra": character.max_chakra,
            "stamina": character.stamina,
            "max_stamina": character.max_stamina,
            "strength": character.strength,
            "defense": character.defense,
            "speed": character.speed,
            "ninjutsu": character.ninjutsu,
            "genjutsu": character.genjutsu,
            "taijutsu": character.taijutsu,
            "wins": character.wins,
            "losses": character.losses,
            "draws": character.draws,
            "wins_against_rank": character.wins_against_rank,
            "exp": character.exp,
            "specialization": character.specialization,
            "willpower": character.willpower,
            "chakra_control": character.chakra_control,
            "intelligence": character.intelligence,
            "perception": character.perception,
            "jutsu": character.jutsu,
            "equipment": character.equipment,
            "inventory": character.inventory,
            "is_active": character.is_active,
            "status_effects": character.status_effects,
            "active_effects": character.active_effects,
            "status_conditions": character.status_conditions,
            "buffs": character.buffs,
            "debuffs": character.debuffs,
            "achievements": character.achievements,
            "titles": character.titles,
            "completed_missions": character.completed_missions,
            "jutsu_mastery": character.jutsu_mastery,
            "last_daily_claim": character.last_daily_claim,
            "active_mission_id": character.active_mission_id
        }

    def _dict_to_character(self, data: Dict) -> Character:
        """Convert dictionary data to Character object."""
        return Character(
            id=data["id"],
            name=data["name"],
            clan=data.get("clan", ""),
            level=data.get("level", 1),
            rank=data.get("rank", "Genin"),
            hp=data.get("hp", 100),
            max_hp=data.get("max_hp", 100),
            chakra=data.get("chakra", 50),
            max_chakra=data.get("max_chakra", 50),
            stamina=data.get("stamina", 50),
            max_stamina=data.get("max_stamina", 50),
            strength=data.get("strength", 10),
            defense=data.get("defense", 5),
            speed=data.get("speed", 5),
            ninjutsu=data.get("ninjutsu", 5),
            genjutsu=data.get("genjutsu", 5),
            taijutsu=data.get("taijutsu", 5),
            wins=data.get("wins", 0),
            losses=data.get("losses", 0),
            draws=data.get("draws", 0),
            wins_against_rank=data.get("wins_against_rank", {}),
            # Additional fields
            exp=data.get("exp", 0),
            specialization=data.get("specialization"),
            willpower=data.get("willpower", 10),
            chakra_control=data.get("chakra_control", 10),
            intelligence=data.get("intelligence", 10),
            perception=data.get("perception", 10),
            jutsu=data.get("jutsu", []),
            equipment=data.get("equipment", {}),
            inventory=data.get("inventory", []),
            is_active=data.get("is_active", True),
            status_effects=data.get("status_effects", []),
            active_effects=data.get("active_effects", {}),
            status_conditions=data.get("status_conditions", {}),
            buffs=data.get("buffs", {}),
            debuffs=data.get("debuffs", {}),
            achievements=data.get("achievements", []),
            titles=data.get("titles", []),
            completed_missions=data.get("completed_missions", []),
            jutsu_mastery=data.get("jutsu_mastery", {}),
            last_daily_claim=data.get("last_daily_claim"),
            active_mission_id=data.get("active_mission_id")
        )

    async def create_character(self, user_id: int, name: str, clan: str = "") -> Character:
        """Create a new character and save to file."""
        char = Character(id=str(user_id), name=name, clan=clan)
        self.characters[str(user_id)] = char
        self._save_character_to_file(char)
        print(f"✅ Created and saved character: {name} for user {user_id}")
        return char

    async def get_character(self, user_id: int) -> Optional[Character]:
        """Get character from memory or load from file if needed."""
        user_id_str = str(user_id)
        
        # Try memory first
        if user_id_str in self.characters:
            return self.characters[user_id_str]
        
        # Try loading from file
        character_data = self._load_character_from_file(user_id_str)
        if character_data:
            char = self._dict_to_character(character_data)
            self.characters[user_id_str] = char
            return char
        
        return None

    async def delete_character(self, user_id: int) -> None:
        """Delete character from memory and file."""
        user_id_str = str(user_id)
        
        # Remove from memory
        self.characters.pop(user_id_str, None)
        
        # Remove file
        try:
            character_file = os.path.join(self.characters_dir, f"{user_id_str}.json")
            if os.path.exists(character_file):
                os.remove(character_file)
                print(f"✅ Deleted character file for user {user_id}")
        except Exception as e:
            print(f"Error deleting character file for {user_id}: {e}")

    async def save_character(self, char: Character) -> None:
        """Save character to memory and file."""
        self.characters[str(char.id)] = char
        self._save_character_to_file(char)

    async def _load_character(self, user_id: str) -> Optional[Character]:
        """Helper method for testing - direct file load."""
        character_data = self._load_character_from_file(user_id)
        if character_data:
            return self._dict_to_character(character_data)
        return None
