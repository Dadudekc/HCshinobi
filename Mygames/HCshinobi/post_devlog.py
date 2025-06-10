import discord
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def post_devlog():
    # Set up the Discord client
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    try:
        # Get the token from environment variables
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("Error: Discord token not found in environment variables")
            return
            
        # Log in to Discord
        await client.login(token)
        await client.connect()
        
        # Get the devlog channel
        channel_id = 1356487107778056214
        channel = await client.fetch_channel(channel_id)
        
        # Create the embed message
        embed = discord.Embed(
            title="🐛 Jutsu Malfunction Report",
            description="Esteemed shinobi of the village, this is an urgent report from the Debugging Division. Our jutsu scrolls are experiencing a chakra disruption.",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Mission Status",
            value="Our ninja commands are unable to flow chakra properly through the Discord channels. The forbidden error '403' has been cast upon our techniques.",
            inline=False
        )
        
        embed.add_field(
            name="Investigation",
            value="Our elite ANBU debugging squad suspects that our bot requires additional permissions to channel its chakra. We are analyzing the chakra pathways now.",
            inline=False
        )
        
        embed.add_field(
            name="Next Steps",
            value="The Hokage has assigned a team of jōnin developers to resolve this issue. Please stand by as we perform the necessary hand signs to restore functionality.",
            inline=False
        )
        
        embed.set_footer(text="This message was sent by the automated debugging system")
        
        # Send the message
        await channel.send(embed=embed)
        print("Debug message sent successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Make sure to close the client
        try:
            await client.close()
        except:
            pass

# Run the function
asyncio.run(post_devlog()) 