import random

class ClanAssignmentEngine:
    def __init__(self) -> None:
        # Updated clan list with all clans from ClanData
        self.clans = [
            # Legendary Clans
            "Uchiha", "Senju", "Uzumaki",
            # Epic Clans  
            "Hyuga", "Aburame", "Inuzuka", "Nara", "Yamanaka", "Akimichi",
            # Rare Clans
            "Sarutobi", "Hatake", "Kaguya", "Hozuki",
            # Uncommon Clans
            "Kazekage", "Mizukage", "Raikage", "Tsuchikage", "Hokage",
            # Common Clans
            "Civilian", "Merchant", "Farmer", "Blacksmith", "Scholar"
        ]
        self.assignments = {}
        
        # Clan rarity mapping
        self.clan_rarities = {
            # Legendary Clans
            "Uchiha": "Legendary", "Senju": "Legendary", "Uzumaki": "Legendary",
            # Epic Clans
            "Hyuga": "Epic", "Aburame": "Epic", "Inuzuka": "Epic", "Nara": "Epic", "Yamanaka": "Epic", "Akimichi": "Epic",
            # Rare Clans
            "Sarutobi": "Rare", "Hatake": "Rare", "Kaguya": "Rare", "Hozuki": "Rare",
            # Uncommon Clans
            "Kazekage": "Uncommon", "Mizukage": "Uncommon", "Raikage": "Uncommon", "Tsuchikage": "Uncommon", "Hokage": "Uncommon",
            # Common Clans
            "Civilian": "Common", "Merchant": "Common", "Farmer": "Common", "Blacksmith": "Common", "Scholar": "Common"
        }

    async def assign_clan(self, user_id: int) -> dict:
        clan = random.choice(self.clans)
        self.assignments[str(user_id)] = clan
        clan_rarity = self.clan_rarities.get(clan, "Common")
        return {"assigned_clan": clan, "clan_rarity": clan_rarity}

    def get_player_clan(self, user_id: int):
        return self.assignments.get(str(user_id))
