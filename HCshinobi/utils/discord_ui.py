"""Utility helpers related to Discord UI components and colours."""

from __future__ import annotations

from discord import Colour

#: Mapping of clan rarity tiers to embed colours
RARITY_COLORS = {
    "Common": Colour.light_grey(),
    "Uncommon": Colour.green(),
    "Rare": Colour.blue(),
    "Epic": Colour.purple(),
    "Legendary": Colour.gold(),
}


def get_rarity_color(rarity: str) -> Colour:
    """Return the colour associated with a given rarity string."""

    return RARITY_COLORS.get(rarity.title(), Colour.default())


__all__ = ["RARITY_COLORS", "get_rarity_color"]
