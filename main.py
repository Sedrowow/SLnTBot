import discord
from discord.ext import commands
import json
import os

# Get configuration.json
with open("configuration.json", "r") as config: 
    data = json.load(config)
    owner_id = data["owner_id"]

# Get token from environment variable or fall back to a .env file
token = os.getenv('DISCORD_BOT_TOKEN')
if not token:
    # Try to load from a .env file using python-dotenv if available
    try:
        from dotenv import load_dotenv
    except Exception:
        raise ValueError("No token found in environment and python-dotenv is not installed. Install python-dotenv or set DISCORD_BOT_TOKEN environment variable.")
    # load .env from project root (default behavior)
    load_dotenv()
    token = os.getenv('DISCORD_BOT_TOKEN')

if not token:
    raise ValueError("No token found! Make sure to set DISCORD_BOT_TOKEN environment variable or create a .env file with DISCORD_BOT_TOKEN=...")

class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,  # Only respond to mentions
            intents=discord.Intents.all(),
            owner_id=owner_id,
            application_id=os.getenv('APPLICATION_ID')
        )

    async def setup_hook(self):
        for filename in os.listdir("Cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"Cogs.{filename[:-3]}")
        await self.tree.sync()

bot = CustomBot()

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    print(discord.__version__)
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="/help"
    ))

bot.run(token)