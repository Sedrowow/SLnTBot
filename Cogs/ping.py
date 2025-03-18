import discord
from discord.ext import commands
from discord import app_commands
import time

class PingCog(commands.Cog, name="ping command"):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="ping", description="Display the bot's ping")
    @app_commands.checks.cooldown(1, 2.0)
    async def ping(self, interaction: discord.Interaction):
        start_time = time.perf_counter()
        await interaction.response.send_message("Pinging...")
        end_time = time.perf_counter()
        await interaction.edit_original_response(
            content=f"Pong! {(end_time - start_time) * 1000:.0f}ms"
        )

async def setup(bot:commands.Bot):
    await bot.add_cog(PingCog(bot))