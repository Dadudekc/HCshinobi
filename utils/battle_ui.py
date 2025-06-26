"""Simplified Discord view helpers for the battle system."""

from __future__ import annotations

import discord


class BattleView(discord.ui.View):
    """Minimal view presenting basic battle actions."""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(AttackButton())


class AttackButton(discord.ui.Button):
    """Simple attack button used in placeholder battles."""

    def __init__(self) -> None:
        super().__init__(style=discord.ButtonStyle.primary, label="Attack")

    async def callback(self, interaction: discord.Interaction) -> None:  # pragma: no cover - trivial
        await interaction.response.send_message("You attack the enemy!", ephemeral=True)


def render_battle_view() -> BattleView:
    """Return a ``BattleView`` instance for use in commands."""

    return BattleView()


__all__ = ["BattleView", "render_battle_view"]
