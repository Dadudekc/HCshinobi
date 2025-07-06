"""Character related slash commands used for testing."""
from __future__ import annotations

from typing import Iterable, Optional

import discord
from discord import app_commands
from discord.ext import commands


class DeleteConfirmationView(discord.ui.View):
    """Simple confirmation view used by the /delete command."""

    def __init__(self, cog: "CharacterCommands", user: discord.User, character) -> None:
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.character = character
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # pragma: no cover - simple behaviour
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This confirmation is not for you.", ephemeral=True)
            return
        await self.cog.character_system.delete_character(self.user.id)
        await interaction.response.edit_message(content="Character deleted", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # pragma: no cover - simple behaviour
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This confirmation is not for you.", ephemeral=True)
            return
        await interaction.response.edit_message(content="Deletion cancelled", view=None)


class CharacterCommands(commands.Cog):
    """Cog implementing basic character commands used throughout the tests."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        # Try to resolve systems from either attributes on the bot or a services container
        services = getattr(bot, "services", None)
        self.character_system = getattr(bot, "character_system", None) or getattr(services, "character_system", None)
        self.clan_assignment_engine = getattr(bot, "clan_assignment_engine", None) or getattr(services, "clan_assignment_engine", None)
        self.currency_system = getattr(bot, "currency_system", None) or getattr(services, "currency_system", None)
        self.token_system = getattr(bot, "token_system", None) or getattr(services, "token_system", None)
        self.jutsu_system = getattr(bot, "jutsu_system", None) or getattr(services, "jutsu_system", None)
        self.item_registry = getattr(bot, "item_registry", None)
        self.ollama_client = getattr(bot, "ollama_client", None) or getattr(services, "ollama_client", None)

    async def _maybe_await(self, value):
        if hasattr(value, "__await__"):
            return await value
        return value

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    async def _get_character(self, user_id: str):
        if self.character_system is None:
            return None
        return await self.character_system.get_character(user_id)

    async def _format_jutsu_list(self, jutsu_ids: Iterable[str]) -> str:
        """Return a newline separated list of jutsu information."""

        if not jutsu_ids:
            return ""
        lines = []
        if self.jutsu_system:
            for jid in jutsu_ids:
                data = self.jutsu_system.get_jutsu(jid)
                if data:
                    name = data.get("name", jid)
                    j_type = data.get("type", "")
                    rank = data.get("rank", "")
                    desc = data.get("description", "")
                    lines.append(f"**{name} ({j_type})**: Rank {rank} - {desc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------
    @app_commands.command(name="create", description="Create a character")
    async def create(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        char = await self._get_character(str(interaction.user.id))
        if char:
            await interaction.followup.send(
                "You already have a Shinobi character! Use `/profile`.",
                ephemeral=True,
            )
            return

        new_char = await self.character_system.create_character(
            str(interaction.user.id), interaction.user.display_name
        )

        clan_name = ""
        if self.clan_assignment_engine:
            result = await self.clan_assignment_engine.assign_clan(str(interaction.user.id))
            clan_name = result.get("assigned_clan", "")

        if self.ollama_client:
            # Best effort call; output ignored
            await self.ollama_client.generate_response(f"welcome {interaction.user.display_name}")

        embed = discord.Embed(
            title="Character Created",
            description=f"Welcome, {new_char.name}! {clan_name}",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View your character")
    async def profile(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        char = await self._get_character(str(interaction.user.id))
        if not char:
            await interaction.followup.send(
                "You don't have a character yet! Use `/create` to start your journey.",
                ephemeral=True,
            )
            return

        ryo = 0
        tokens = 0
        if self.currency_system:
            ryo = await self._maybe_await(self.currency_system.get_player_balance(str(interaction.user.id)))
        if self.token_system:
            tokens = await self._maybe_await(self.token_system.get_player_tokens(str(interaction.user.id)))

        embed = discord.Embed(title=f"{interaction.user.display_name}'s Shinobi Profile")
        embed.add_field(name="⚜️ Clan", value=getattr(char, "clan", "N/A"), inline=False)
        embed.add_field(name="📊 Stats", value=f"Level: {getattr(char, 'level', 1)}", inline=False)
        combat_stats = (
            f"**Taijutsu:** {getattr(char, 'taijutsu', 0)}\n"
            f"**Ninjutsu:** {getattr(char, 'ninjutsu', 0)}\n"
            f"**Genjutsu:** {getattr(char, 'genjutsu', 0)}"
        )
        embed.add_field(name="Combat Stats", value=combat_stats, inline=False)
        embed.add_field(name="💰 Currency", value=f"**Ryō:** {ryo}\n**Tokens:** {tokens}", inline=False)
        embed.set_footer(text="Use /stats for detailed stats and battle record.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="View character stats")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        target = user or interaction.user
        ephemeral = user is None
        await interaction.response.defer(ephemeral=ephemeral)

        char = await self._get_character(str(target.id))
        if not char:
            msg = (
                "You don't have a character yet! Use `/create` to start your journey." if user is None
                else f"User <@{target.id}> does not have a character."
            )
            await interaction.followup.send(msg, ephemeral=True)
            return

        core_stats = (
            f"❤️ **HP:** {getattr(char, 'hp', 0)}/{getattr(char, 'max_hp', 0)}\n"
            f"🔋 **Chakra:** {getattr(char, 'chakra', 0)}/{getattr(char, 'max_chakra', 0)}\n"
            f"🏃 **Stamina:** {getattr(char, 'stamina', 0)}/{getattr(char, 'max_stamina', 0)}\n"
            f"💪 **Strength:** {getattr(char, 'strength', 0)}\n"
            f"⚡ **Speed:** {getattr(char, 'speed', 0)}\n"
            f"🛡️ **Defense:** {getattr(char, 'defense', 0)}\n"
            f"🧠 **Intelligence:** {getattr(char, 'intelligence', 0)}\n"
            f"👁️ **Perception:** {getattr(char, 'perception', 0)}\n"
            f"💥 **Willpower:** {getattr(char, 'willpower', 0)}\n"
            f"✨ **Chakra Control:** {getattr(char, 'chakra_control', 0)}"
        )

        combat_stats = (
            f"🥋 **Taijutsu:** {getattr(char, 'taijutsu', 0)}\n"
            f"🔥 **Ninjutsu:** {getattr(char, 'ninjutsu', 0)}\n"
            f"🌀 **Genjutsu:** {getattr(char, 'genjutsu', 0)}"
        )

        total_fights = getattr(char, "wins", 0) + getattr(char, "losses", 0) + getattr(char, "draws", 0)
        win_rate = (getattr(char, "wins", 0) / total_fights * 100) if total_fights else 0
        battle_record = (
            f"🏆 **Wins:** {getattr(char, 'wins', 0)}\n"
            f"☠️ **Losses:** {getattr(char, 'losses', 0)}\n"
            f"🤝 **Draws:** {getattr(char, 'draws', 0)}\n"
            f"📈 **Win Rate:** {win_rate:.1f}%"
        )

        wins_vs_rank = getattr(char, "wins_against_rank", {})
        wins_rank_lines = [f"- vs {rank}: {count}" for rank, count in sorted(wins_vs_rank.items())]

        embed = discord.Embed(
            title=f"📊 {char.name}'s Stats & Record",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Core Stats", value=core_stats, inline=False)
        embed.add_field(name="Combat Stats", value=combat_stats, inline=False)
        embed.add_field(name="Battle Record", value=battle_record, inline=False)
        embed.add_field(name="Wins vs Rank", value="\n".join(wins_rank_lines) if wins_rank_lines else "None", inline=False)
        embed.set_footer(text=f"ID: {target.id}")
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)

    @app_commands.command(name="inventory", description="Show your inventory")
    async def inventory(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        char = await self._get_character(str(interaction.user.id))
        if not char:
            await interaction.followup.send(
                "You don't have a character yet! Use `/create` to start your journey.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title=f"🎒 {char.name}'s Inventory")

        items = getattr(char, "inventory", {}) or {}
        if not items:
            embed.description = "Empty"
        else:
            lines = []
            registry = self.item_registry or getattr(self.bot, "item_registry", None)
            for item_id, qty in items.items():
                item = None
                if registry:
                    item = registry.get_item(item_id)
                if item:
                    line = f"**{item.get('name')} ({item.get('rarity')})**: {qty} - {item.get('description')}"
                else:
                    line = f"{item_id}: {qty}"
                lines.append(line)
            embed.description = "\n".join(lines)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="jutsu", description="Show known jutsu")
    async def jutsu(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        char = await self._get_character(str(interaction.user.id))
        if not char:
            await interaction.followup.send(
                "You don't have a character yet! Use `/create` to start your journey.",
                ephemeral=True,
            )
            return

        jutsu_ids = getattr(char, "jutsu", []) or []
        description = "None learned"
        if jutsu_ids:
            description = await self._format_jutsu_list(jutsu_ids)

        embed = discord.Embed(title=f"📜 {char.name}'s Known Jutsu", description=description)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="Delete your character")
    async def delete(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        char = await self._get_character(str(interaction.user.id))
        if not char:
            await interaction.followup.send(
                "You don't have a character yet! Use `/create` to start your journey.",
                ephemeral=True,
            )
            return

        view = DeleteConfirmationView(self, interaction.user, char)
        message = await interaction.followup.send(
            f"**Warning!** Are you sure you want to delete your character **{char.name}**? This action cannot be undone.",
            view=view,
            ephemeral=True,
        )
        view.message = message


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCommands(bot))
