"""Core views for Discord interactions."""
import discord
from typing import Optional


class ConfirmView(discord.ui.View):
    """A view for confirming or canceling an action."""
    
    def __init__(self, user: discord.User, timeout: Optional[float] = 180):
        """Initialize the confirm view.
        
        Args:
            user: The user who can interact with the view
            timeout: View timeout in seconds (default: 180)
        """
        super().__init__(timeout=timeout)
        self.user = user
        self.value = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the correct user.
        
        Args:
            interaction: The Discord interaction
            
        Returns:
            bool: Whether the interaction is valid
        """
        if interaction.user != self.user:
            await interaction.response.send_message(
                "This confirmation is not for you.",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle the confirm button click.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        self.value = True
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red,
        emoji="❌"
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle the cancel button click.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        self.value = False
        await interaction.response.defer()
        self.stop()


class PaginationView(discord.ui.View):
    """A view for paginating through content."""
    
    def __init__(
        self,
        pages: list[discord.Embed],
        user: discord.User,
        timeout: Optional[float] = 180
    ):
        """Initialize the pagination view.
        
        Args:
            pages: List of embeds to paginate through
            user: The user who can interact with the view
            timeout: View timeout in seconds (default: 180)
        """
        super().__init__(timeout=timeout)
        self.pages = pages
        self.user = user
        self.current_page = 0
        
        # Update button states
        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = len(self.pages) <= 1
        self.last_page.disabled = len(self.pages) <= 1
        
        # Update page counter
        self.page_counter.label = f"Page {self.current_page + 1}/{len(self.pages)}"
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the correct user.
        
        Args:
            interaction: The Discord interaction
            
        Returns:
            bool: Whether the interaction is valid
        """
        if interaction.user != self.user:
            await interaction.response.send_message(
                "This pagination is not for you.",
                ephemeral=True
            )
            return False
        return True
    
    def update_buttons(self):
        """Update the state of navigation buttons."""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.pages) - 1
        self.last_page.disabled = self.current_page == len(self.pages) - 1
        self.page_counter.label = f"Page {self.current_page + 1}/{len(self.pages)}"
    
    @discord.ui.button(
        label="⏮️",
        style=discord.ButtonStyle.blurple,
        custom_id="first_page"
    )
    async def first_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Go to the first page.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page],
            view=self
        )
    
    @discord.ui.button(
        label="◀️",
        style=discord.ButtonStyle.blurple,
        custom_id="prev_page"
    )
    async def prev_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Go to the previous page.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page],
            view=self
        )
    
    @discord.ui.button(
        label="Page 1/1",
        style=discord.ButtonStyle.gray,
        custom_id="page_counter",
        disabled=True
    )
    async def page_counter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Page counter button (disabled).
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        pass
    
    @discord.ui.button(
        label="▶️",
        style=discord.ButtonStyle.blurple,
        custom_id="next_page"
    )
    async def next_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Go to the next page.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page],
            view=self
        )
    
    @discord.ui.button(
        label="⏭️",
        style=discord.ButtonStyle.blurple,
        custom_id="last_page"
    )
    async def last_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Go to the last page.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        self.current_page = len(self.pages) - 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page],
            view=self
        ) 