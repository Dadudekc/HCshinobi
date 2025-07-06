import pytest
from unittest.mock import AsyncMock, MagicMock

from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine

@pytest.mark.asyncio
async def test_complete_mission_awards_rewards(tmp_path):
    currency = MagicMock(spec=CurrencySystem)
    progression = AsyncMock(spec=ShinobiProgressionEngine)

    data_dir = tmp_path
    missions = MissionSystem(str(data_dir), currency_system=currency, progression_engine=progression)
    missions.definitions = [
        {"mission_id": "m1", "title": "Test", "reward_ryo": 10, "reward_exp": 5}
    ]

    await missions.assign_mission("user", "m1")
    success, msg, rewards = await missions.complete_mission("user")

    assert success
    assert rewards["ryo"] == 10
    assert rewards["exp"] == 5
    currency.add_balance_and_save.assert_called_once_with("user", 10)
    progression.award_mission_experience.assert_awaited_once_with("user", 5)
