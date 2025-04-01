"""Training commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from typing import Optional
import logging
import asyncio

from HCshinobi.core.training_system import TrainingSystem, TrainingIntensity
from HCshinobi.core.character_system import CharacterSystem

class TrainingCommands(commands.Cog):
    def __init__(self, bot, training_system: TrainingSystem, character_system: CharacterSystem):
        """Initialize training commands.
        
        Args:
            bot: The bot instance
            training_system: The training system instance
            character_system: The character system instance
        """
        self.bot = bot
        self.training_system = training_system
        self.character_system = character_system
        self.logger = logging.getLogger(__name__)

    async def cog_command_error(self, ctx, error):
        """Handle errors for all commands in this cog."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have permission to do that!")
        else:
            self.logger.error(f"Error in {ctx.command.name}: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="train",
        aliases=["practice", "workout"],
        description="Start training a specific attribute",
        help="Train an attribute for a specified duration and intensity."
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def train(self, ctx, attribute: str, duration_hours: int, intensity: str = TrainingIntensity.MODERATE):
        """Start training a specific attribute.
        
        Args:
            ctx: The command context
            attribute: The attribute to train
            duration_hours: How long to train (in hours)
            intensity: Training intensity (light, moderate, intense, extreme)
        """
        try:
            # Validate intensity
            if intensity not in [TrainingIntensity.LIGHT, TrainingIntensity.MODERATE, 
                              TrainingIntensity.INTENSE, TrainingIntensity.EXTREME]:
                await ctx.send("❌ Invalid intensity level! Choose from: light, moderate, intense, extreme")
                return
            
            # Get character
            character = self.character_system.get_character(str(ctx.author.id))
            if not character:
                await ctx.send("❌ You need a character to train! Use !create to create one.")
                return
            
            # Validate duration
            if duration_hours < 1 or duration_hours > 24:
                await ctx.send("❌ Training duration must be between 1 and 24 hours!")
                return
            
            # Get training cost
            cost_per_hour = self.training_system.get_training_cost(attribute, intensity)
            total_cost = cost_per_hour * duration_hours
            
            # Start training
            success, message = self.training_system.start_training(
                str(ctx.author.id),
                attribute,
                duration_hours,
                intensity
            )
            
            if not success:
                await ctx.send(f"❌ {message}")
                return
            
            # Create embed
            embed = discord.Embed(
                title="🏋️ Training Started",
                description=message,
                color=discord.Color.blue()
            )
            embed.add_field(name="Attribute", value=attribute, inline=True)
            embed.add_field(name="Duration", value=f"{duration_hours} hours", inline=True)
            embed.add_field(name="Intensity", value=intensity.title(), inline=True)
            embed.add_field(name="Cost per Hour", value=f"{cost_per_hour} Ryō", inline=True)
            embed.add_field(name="Total Cost", value=f"{total_cost} Ryō", inline=True)
            
            # Add intensity multipliers
            cost_mult, gain_mult = TrainingIntensity.get_multipliers(intensity)
            embed.add_field(
                name="Training Multipliers",
                value=f"Cost: {cost_mult}x, Gain: {gain_mult}x",
                inline=False
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in train command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    @commands.command(
        name="complete",
        aliases=["finish", "done"],
        description="Complete your current training session",
        help="Complete your current training and claim your results."
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def complete(self, ctx):
        """Complete current training session.
        
        Args:
            ctx: The command context
        """
        try:
            # Get character
            character = self.character_system.get_character(str(ctx.author.id))
            if not character:
                await ctx.send("❌ You need a character to complete training! Use !create to create one.")
                return
            
            # Complete training
            success, message, results = self.training_system.complete_training(
                str(ctx.author.id),
                character
            )
            
            if not success:
                await ctx.send(f"❌ {message}")
                return
            
            # Save character changes
            self.character_system.update_character(str(ctx.author.id), character)
            
            # Create embed
            embed = discord.Embed(
                title="🏆 Training Complete",
                description=message,
                color=discord.Color.green()
            )
            embed.add_field(name="Attribute", value=results['attribute'], inline=True)
            embed.add_field(name="Points Gained", value=str(results['increase']), inline=True)
            embed.add_field(name="Hours Trained", value=str(results['hours_trained']), inline=True)
            embed.add_field(name="Intensity", value=results['intensity'].title(), inline=True)
            embed.add_field(name="Total Cost", value=f"{results['cost']} Ryō", inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in complete command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    @commands.command(
        name="cancel_training",
        aliases=["cancel", "stop"],
        description="Cancel your current training session",
        help="Cancel your current training session without receiving benefits."
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def cancel_training(self, ctx):
        """Cancel current training session.
        
        Args:
            ctx: The command context
        """
        try:
            # Get character
            character = self.character_system.get_character(str(ctx.author.id))
            if not character:
                await ctx.send("❌ You need a character to cancel training! Use !create to create one.")
                return
            
            # Cancel training
            success, message = self.training_system.cancel_training(str(ctx.author.id))
            
            embed = discord.Embed(
                title="❌ Training Cancelled",
                description=message,
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in cancel_training command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    @commands.command(
        name="training_status",
        aliases=["train_status", "progress"],
        description="Check your current training status",
        help="View details about your ongoing training session."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def training_status(self, ctx):
        """Check your current training status.
        
        Args:
            ctx: The command context
        """
        try:
            # Get character
            character = self.character_system.get_character(str(ctx.author.id))
            if not character:
                await ctx.send("❌ You need a character to check training status! Use !create to create one.")
                return
            
            # Get training status
            training_session = self.training_system.get_training_session(str(ctx.author.id))
            
            if not training_session:
                await ctx.send("❌ You don't have an active training session!")
                return
            
            # Calculate time remaining
            time_elapsed, time_remaining = self.training_system.get_training_time_info(training_session)
            
            # Get estimated gains
            estimated_gains = self.training_system.get_estimated_gains(training_session)
            
            # Create embed
            embed = discord.Embed(
                title="🏋️ Training Status",
                description=f"Current training status for {character.name}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Attribute", value=training_session['attribute'], inline=True)
            embed.add_field(name="Duration", value=f"{training_session['duration']} hours", inline=True)
            embed.add_field(name="Intensity", value=training_session['intensity'].title(), inline=True)
            
            embed.add_field(name="Time Elapsed", value=f"{time_elapsed:.1f} hours", inline=True)
            embed.add_field(name="Time Remaining", value=f"{time_remaining:.1f} hours", inline=True)
            embed.add_field(name="Estimated Gains", value=f"+{estimated_gains:.1f} points", inline=True)
            
            embed.add_field(name="Progress", value=f"{min(100, time_elapsed / training_session['duration'] * 100):.1f}%", inline=False)
            
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in training_status command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    @commands.command(
        name="training_history",
        aliases=["history", "records"],
        description="View your training history and achievements",
        help="See your past training sessions and total gains."
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def training_history(self, ctx):
        """View your training history and achievements.
        
        Args:
            ctx: The command context
        """
        try:
            # Get character
            character = self.character_system.get_character(str(ctx.author.id))
            if not character:
                await ctx.send("❌ You need a character to view training history! Use !create to create one.")
                return
            
            # Get training history
            history = self.training_system.get_training_history(str(ctx.author.id))
            
            if not history:
                await ctx.send("❌ You don't have any training history yet!")
                return
            
            # Calculate stats
            total_sessions = len(history)
            total_hours = sum(session.get('hours_trained', 0) for session in history)
            total_gains = sum(session.get('increase', 0) for session in history)
            
            attribute_stats = {}
            for session in history:
                attr = session.get('attribute', 'Unknown')
                if attr not in attribute_stats:
                    attribute_stats[attr] = {
                        'sessions': 0,
                        'hours': 0,
                        'gains': 0
                    }
                attribute_stats[attr]['sessions'] += 1
                attribute_stats[attr]['hours'] += session.get('hours_trained', 0)
                attribute_stats[attr]['gains'] += session.get('increase', 0)
            
            # Create embed
            embed = discord.Embed(
                title="📚 Training History",
                description=f"Training history for {character.name}",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Total Sessions", value=str(total_sessions), inline=True)
            embed.add_field(name="Total Hours", value=str(total_hours), inline=True)
            embed.add_field(name="Total Gains", value=str(total_gains), inline=True)
            
            # Add attribute breakdowns
            for attr, stats in attribute_stats.items():
                embed.add_field(
                    name=f"{attr} Training",
                    value=f"Sessions: {stats['sessions']}\nHours: {stats['hours']}\nGains: {stats['gains']}",
                    inline=True
                )
            
            # Add recent sessions
            recent_sessions = history[-5:] if len(history) > 5 else history
            recent_text = ""
            for i, session in enumerate(reversed(recent_sessions)):
                recent_text += f"{i+1}. {session.get('attribute', 'Unknown')}: +{session.get('increase', 0)} ({session.get('intensity', 'Unknown').title()})\n"
            
            embed.add_field(
                name="Recent Sessions",
                value=recent_text or "None",
                inline=False
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in training_history command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

async def setup(bot):
    """Set up the training commands cog."""
    await bot.add_cog(TrainingCommands(bot, bot.training_system, bot.character_system)) 