import os
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the bot token
token = os.getenv('DISCORD_BOT_TOKEN')
if not token:
    print("Error: DISCORD_BOT_TOKEN not found in environment variables")
    exit(1)

# Create bot instance
intents = discord.Intents.all()
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready: {bot.user.name}')

# Run the bot
bot.run(token) 