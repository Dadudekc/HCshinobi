import os
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CharacterCreator:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.characters_dir = os.path.join(data_dir, "characters")
        self.template_path = os.path.join(self.characters_dir, "template.json")
        self._ensure_directories()
        self._load_template()

    def _ensure_directories(self):
        """Ensure the data and characters directories exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.characters_dir, exist_ok=True)

    def _load_template(self):
        """Load the character template."""
        if os.path.exists(self.template_path):
            with open(self.template_path, 'r', encoding='utf-8') as f:
                self.template = json.load(f)
        else:
            logger.warning("Template file not found. Using default template.")
            self.template = {
                "identity": {
                    "name": "",
                    "titles": [],
                    "village": "",
                    "clan": "",
                    "rank": "",
                    "role_status": "",
                    "jinchuriki": "",
                    "affiliations": []
                },
                "base_stats": {
                    "hp": 100,
                    "chakra_pool": 100,
                    "strength": 100,
                    "speed": 100,
                    "ninjutsu_power": 100,
                    "taijutsu_power": 100,
                    "genjutsu_resist": 100,
                    "chakra_regen_rate": 10
                },
                "appearance": {
                    "height": "",
                    "eyes": "",
                    "hair": "",
                    "build": "",
                    "attire": []
                },
                "philosophy": {
                    "core_beliefs": [],
                    "guiding_quote": ""
                },
                "backstory": {
                    "clan_history": "",
                    "training": "",
                    "key_events": []
                }
            }

    def _get_input(self, prompt: str, required: bool = True) -> str:
        """Get user input with validation."""
        while True:
            value = input(prompt).strip()
            if not value and required:
                print("This field is required. Please try again.")
            else:
                return value

    def _get_list_input(self, prompt: str) -> List[str]:
        """Get a list of items from user input."""
        print(prompt)
        print("Enter items one per line. Press Enter twice when done.")
        items = []
        while True:
            item = input().strip()
            if not item:
                break
            items.append(item)
        return items

    def _get_number_input(self, prompt: str, min_val: int = 0, max_val: int = 1000) -> int:
        """Get a number input with validation."""
        while True:
            try:
                value = int(input(prompt))
                if min_val <= value <= max_val:
                    return value
                print(f"Please enter a number between {min_val} and {max_val}")
            except ValueError:
                print("Please enter a valid number")

    def create_character(self):
        """Guide the user through character creation."""
        print("\n=== Character Creation Wizard ===\n")
        
        # Basic Information
        print("Basic Information:")
        print("-" * 20)
        name = self._get_input("Character Name: ")
        titles = self._get_list_input("Enter titles (one per line):")
        village = self._get_input("Village: ")
        clan = self._get_input("Clan: ")
        rank = self._get_input("Rank: ")
        role_status = self._get_input("Role Status: ")
        jinchuriki = self._get_input("Jinchuriki Status (if any): ", required=False)
        affiliations = self._get_list_input("Enter affiliations (one per line):")

        # Base Stats
        print("\nBase Stats:")
        print("-" * 20)
        base_stats = {
            "hp": self._get_number_input("HP (0-1000): ", 0, 1000),
            "chakra_pool": self._get_number_input("Chakra Pool (0-1000): ", 0, 1000),
            "strength": self._get_number_input("Strength (0-1000): ", 0, 1000),
            "speed": self._get_number_input("Speed (0-1000): ", 0, 1000),
            "ninjutsu_power": self._get_number_input("Ninjutsu Power (0-1000): ", 0, 1000),
            "taijutsu_power": self._get_number_input("Taijutsu Power (0-1000): ", 0, 1000),
            "genjutsu_resist": self._get_number_input("Genjutsu Resistance (0-1000): ", 0, 1000),
            "chakra_regen_rate": self._get_number_input("Chakra Regeneration Rate (0-100): ", 0, 100)
        }

        # Appearance
        print("\nAppearance:")
        print("-" * 20)
        appearance = {
            "height": self._get_input("Height: "),
            "eyes": self._get_input("Eye Color/Description: "),
            "hair": self._get_input("Hair Description: "),
            "build": self._get_input("Build Description: "),
            "attire": self._get_list_input("Enter attire items (one per line):")
        }

        # Philosophy
        print("\nPhilosophy:")
        print("-" * 20)
        philosophy = {
            "core_beliefs": self._get_list_input("Enter core beliefs (one per line):"),
            "guiding_quote": self._get_input("Guiding Quote: ", required=False)
        }

        # Backstory
        print("\nBackstory:")
        print("-" * 20)
        backstory = {
            "clan_history": self._get_input("Clan History: ", required=False),
            "training": self._get_input("Training Background: ", required=False),
            "key_events": self._get_list_input("Enter key events (one per line):")
        }

        # Create character data
        character_data = {
            "identity": {
                "name": name,
                "titles": titles,
                "village": village,
                "clan": clan,
                "rank": rank,
                "role_status": role_status,
                "jinchuriki": jinchuriki,
                "affiliations": affiliations
            },
            "base_stats": base_stats,
            "appearance": appearance,
            "philosophy": philosophy,
            "backstory": backstory
        }

        # Save character
        filename = f"{name.lower().replace(' ', '_')}.json"
        filepath = os.path.join(self.characters_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, indent=4, ensure_ascii=False)
            print(f"\nCharacter saved successfully to: {filepath}")
        except Exception as e:
            print(f"Error saving character: {e}")

def main():
    creator = CharacterCreator()
    creator.create_character()

if __name__ == "__main__":
    main() 