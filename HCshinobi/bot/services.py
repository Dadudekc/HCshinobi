from typing import Optional
from .config import BotConfig
from ..core.character_system import CharacterSystem
from ..core.currency_system import CurrencySystem
from ..core.token_system import TokenSystem
from ..core.training_system import TrainingSystem
from ..core.clan_assignment_engine import ClanAssignmentEngine
from ..core.progression_engine import ShinobiProgressionEngine
from ..core.clan_data import ClanData
from ..core.battle.persistence import BattlePersistence
from ..core.unified_jutsu_system import UnifiedJutsuSystem

class ServiceContainer:
    def __init__(self, config_or_dir: Optional[BotConfig | str] = None, data_dir: Optional[str] = None):
        if isinstance(config_or_dir, BotConfig):
            self.config = config_or_dir
            self.data_dir = config_or_dir.data_dir
        else:
            self.config = None
            self.data_dir = config_or_dir or data_dir or "data"

        self.character_system = CharacterSystem()
        self.currency_system = CurrencySystem()
        self.token_system = TokenSystem()
        self.jutsu_system = UnifiedJutsuSystem()
        self.training_system = TrainingSystem(
            currency_system=self.currency_system,
            character_system=self.character_system,
        )
        self.clan_assignment_engine = ClanAssignmentEngine()
        self.progression_engine = ShinobiProgressionEngine(
            character_system=self.character_system,
            jutsu_system=self.jutsu_system
        )
        self.clan_data = ClanData(self.data_dir)
        self.battle_persistence = BattlePersistence(self.data_dir)
        self.jutsu_shop_system = None
        self.equipment_shop_system = None
        self.ollama_client = None
        self._initialized = False

    async def initialize(self, bot=None):
        self._initialized = True

    async def run_ready_hooks(self):
        pass

    async def shutdown(self):
        pass
