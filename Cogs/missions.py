import discord
from discord.ext import commands
import json
import datetime
from discord.ui import Button, View
from discord import app_commands

class MissionCog(commands.Cog, name="mission commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)
        with open("configuration.json", "r") as f:
            self.config = json.load(f)

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    @commands.command(name="startmission")
    async def start_mission(self, ctx, category: str, *, description: str):
        if category not in self.config["mission_categories"]:
            await ctx.send("Invalid category. Available categories: " + ", ".join(self.config["mission_categories"]))
            return

        mission_id = str(len(self.data["missions"]) + 1)
        mission = {
            "id": mission_id,
            "leader": ctx.author.id,
            "category": category,
            "description": description,
            "status": "pending",
            "start_time": datetime.datetime.now().isoformat(),
            "members": [ctx.author.id],
            "helpers_needed": 0
        }

        self.data["active_missions"][mission_id] = mission
        self.save_data()

        # Create buttons for mission management
        view = View()
        need_help_button = Button(label="Need Help", style=discord.ButtonStyle.primary)
        start_button = Button(label="Start Mission", style=discord.ButtonStyle.green)
        
        async def need_help_callback(interaction):
            # Implementation for requesting help
            pass

        async def start_callback(interaction):
            # Implementation for starting the mission
            pass

        need_help_button.callback = need_help_callback
        start_button.callback = start_callback
        view.add_item(need_help_button)
        view.add_item(start_button)

        await ctx.send(f"Mission {mission_id} created!", view=view)

    @app_commands.command(name="startmission", description="Start a new mission")
    @app_commands.choices(category=[
        app_commands.Choice(name=cat, value=cat) 
        for cat in ["Rescue", "Transport", "Delivery", "Training", "Other"]
    ])
    async def start_mission_slash(self, interaction: discord.Interaction, category: app_commands.Choice[str], description: str):
        if category.value not in self.config["mission_categories"]:
            await interaction.response.send_message(
                "Invalid category. Available categories: " + ", ".join(self.config["mission_categories"]))
            return

        mission_id = str(len(self.data["missions"]) + 1)
        mission = {
            "id": mission_id,
            "leader": interaction.user.id,
            "category": category.value,
            "description": description,
            "status": "pending",
            "start_time": datetime.datetime.now().isoformat(),
            "members": [interaction.user.id],
            "helpers_needed": 0
        }

        self.data["active_missions"][mission_id] = mission
        self.save_data()

        view = View()
        need_help_button = Button(label="Need Help", style=discord.ButtonStyle.primary)
        start_button = Button(label="Start Mission", style=discord.ButtonStyle.green)
        
        async def need_help_callback(button_interaction):
            await button_interaction.response.send_message("Help requested!", ephemeral=True)
            # Additional help request logic here

        async def start_callback(button_interaction):
            await button_interaction.response.send_message("Mission started!", ephemeral=True)
            # Additional mission start logic here

        need_help_button.callback = need_help_callback
        start_button.callback = start_callback
        view.add_item(need_help_button)
        view.add_item(start_button)

        await interaction.response.send_message(f"Mission {mission_id} created!", view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(MissionCog(bot))
