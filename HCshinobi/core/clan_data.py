class ClanData:
    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = data_dir or "data/clans"
        self.clans = {"Uchiha": {}, "Hyuga": {}}

    async def get_clan_by_name(self, name: str):
        return self.clans.get(name)

    async def get_all_clans(self):
        return list(self.clans.keys())

    def create_default_clans(self):
        return self.clans
