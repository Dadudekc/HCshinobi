from __future__ import annotations

import aiohttp
import json
import uuid
from typing import List
from datetime import timedelta

from . import Mission, MissionDifficulty

class MissionGenerator:
    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def generate_mission(self, village: str, difficulty: MissionDifficulty) -> Mission:
        payload = {"village": village, "difficulty": difficulty.value}
        assert self.session is not None
        async with self.session.post("http://localhost", json=payload) as resp:
            data = await resp.json()
        details = json.loads(data.get("response", "{}"))
        return Mission(
            id=str(uuid.uuid4()),
            title=details.get("title", "Mission"),
            description=details.get("description", ""),
            difficulty=difficulty,
            village=village,
            reward=details.get("reward", {}),
            duration=timedelta(hours=details.get("duration_hours", 1)),
            requirements=details.get("requirements", {}),
        )

    async def generate_mission_batch(
        self, village: str, difficulties: List[MissionDifficulty], count: int
    ) -> List[Mission]:
        missions: List[Mission] = []
        for diff in difficulties:
            for _ in range(count):
                missions.append(await self.generate_mission(village, diff))
        return missions
