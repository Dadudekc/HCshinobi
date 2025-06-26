"""Placeholder Discord UI utilities."""

from discord import Colour

RARITY_COLORS = {
    "Common": Colour.light_grey(),
    "Uncommon": Colour.green(),
    "Rare": Colour.blue(),
    "Legendary": Colour.gold(),
}

def get_rarity_color(rarity: str) -> Colour:
    return RARITY_COLORS.get(rarity, Colour.default())
