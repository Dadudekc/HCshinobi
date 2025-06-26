import asyncio
from typing import Any

from .config import BotConfig
from ..core import (
    CharacterSystem,
    CurrencySystem,
    TokenSystem,
    TrainingSystem,
    BattleSystem,
    MissionSystem,
)


class ServiceContainer:
    def __init__(self, config: BotConfig | None = None, data_dir: str | None = None) -> None:
        self.config = config or BotConfig(data_dir=data_dir or "data")
        self._instances: dict[str, Any] = {}
        self.bot = None

    def _get(self, key: str, factory):
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

    @property
    def character_system(self) -> CharacterSystem:
        return self._get("character_system", CharacterSystem)

    @property
    def currency_system(self) -> CurrencySystem:
        return self._get("currency_system", CurrencySystem)

    @property
    def token_system(self) -> TokenSystem:
        return self._get("token_system", TokenSystem)

    @property
    def training_system(self) -> TrainingSystem:
        return self._get("training_system", TrainingSystem)

    @property
    def battle_system(self) -> BattleSystem:
        return self._get("battle_system", BattleSystem)

    @property
    def mission_system(self) -> MissionSystem:
        return self._get("mission_system", MissionSystem)

    async def initialize(self, bot) -> None:
        self.bot = bot
        await self.run_ready_hooks()

    async def run_ready_hooks(self) -> None:
        for service in self._instances.values():
            hook = getattr(service, "ready_hook", None)
            if hook:
                result = hook()
                if asyncio.iscoroutine(result):
                    await result

    async def shutdown(self) -> None:
        for service in self._instances.values():
            close = getattr(service, "close", None)
            if close:
                result = close()
                if asyncio.iscoroutine(result):
                    await result
        self._instances.clear()
