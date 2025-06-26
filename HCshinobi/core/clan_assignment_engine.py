import random

class ClanAssignmentEngine:
    def __init__(self) -> None:
        self.clans = ["Uchiha", "Hyuga", "Senju"]
        self.assignments = {}

    async def assign_clan(self, user_id: int) -> dict:
        clan = random.choice(self.clans)
        self.assignments[str(user_id)] = clan
        return {"assigned_clan": clan}

    def get_player_clan(self, user_id: int):
        return self.assignments.get(str(user_id))
