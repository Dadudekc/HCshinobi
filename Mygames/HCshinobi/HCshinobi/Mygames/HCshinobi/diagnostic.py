import os
import discord
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    # Set up the Discord client
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    try:
        # Get the bot token
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("Error: No Discord token found in environment variables")
            return
        
        # Login and connect
        await client.login(token)
        await client.connect()
        
        # DevLog channel ID
        channel_id = 1356487107778056214
        channel = await client.fetch_channel(channel_id)
        
        # Create the diagnostic embed
        embed = discord.Embed(
            title="🐛 Chakra Network Disruption",
            description="Honorable Hokage, the ANBU Black Ops investigation unit has identified critical issues with our command network!",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Issue Report",
            value="None of our ninja tools (commands) are responding to shinobi requests. Our chakra network appears connected, but jutsu commands fail to manifest.",
            inline=False
        )
        
        embed.add_field(
            name="Investigation Findings",
            value=(
                "1. **Command Channel Restriction**: Commands may be limited to channel ID 1356639366742802603\n"
                "2. **Permission Barriers**: The bot's role permissions may need adjustment\n"
                "3. **Interaction Handling**: Our command response system isn't properly acknowledging user jutsu attempts\n"
                "4. **Discord API Connection**: The bot may be experiencing connection instability"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Solutions Path",
            value=(
                "1. Try using commands in the designated command channel only\n"
                "2. Verify bot has necessary permissions (Send Messages, Read Message History, Use Slash Commands)\n"
                "3. Check Discord Developer Portal and ensure bot privileged intents are enabled\n"
                "4. Restart the bot with debugging enabled (`DEBUG=1` in .env file)\n"
                "5. Simplify the command structure to isolate the failing components"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Next Steps",
            value=(
                "The ANBU debugging squad will focus on isolating each potential issue. "
                "We will first verify command recognition is working, and then move to "
                "command execution and response handling. Our mission is to restore full "
                "functionality to the village's command system."
            ),
            inline=False
        )
        
        # Send the embed
        await channel.send(embed=embed)
        print("Diagnostic message sent successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            await client.close()
        except:
            pass

# Run the script
if __name__ == "__main__":
    asyncio.run(main()) 