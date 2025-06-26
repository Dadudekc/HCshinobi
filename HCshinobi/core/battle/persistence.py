class BattlePersistence:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.active_battles = {}
        self.battle_history = {}

    async def add_active_battle(self, battle_id: str, battle_state):
        self.active_battles[battle_id] = battle_state

    async def remove_active_battle(self, battle_id: str):
        self.active_battles.pop(battle_id, None)

    async def load_active_battles(self):
        return self.active_battles

    async def save_active_battles(self):
        pass

    async def add_battle_to_history(self, battle_id: str, battle_state):
        self.battle_history.setdefault(battle_id, []).extend(battle_state.battle_log)

    async def load_battle_history(self):
        return self.battle_history

    async def save_battle_history(self):
        pass
