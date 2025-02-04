import discord
from discord.ext import commands
from discord import app_commands
import json

class LevelsCog(commands.Cog, name="leveling commands"):
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

    @commands.command(name="approve")
    @commands.has_role("Manager")
    async def approve_mission(self, ctx, user: discord.Member, mission_id: str, sc: int, exp: int):
        user_id = str(user.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
        
        self.data["users"][user_id]["sc"] += sc
        self.data["users"][user_id]["exp"] += exp
        self.save_data()

        await ctx.send(f"Mission approved! {user.mention} received {sc} SC and {exp} EXP")

    @app_commands.command(name="approve", description="Approve a mission and award SC/EXP")
    @app_commands.checks.has_role("Manager")
    async def approve_slash(self, interaction: discord.Interaction, user: discord.Member, mission_id: str, sc: int, exp: int):
        user_id = str(user.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
        
        self.data["users"][user_id]["sc"] += sc
        self.data["users"][user_id]["exp"] += exp
        self.save_data()

        # Check for level up
        current_exp = self.data["users"][user_id]["exp"]
        new_level = 1
        for level, req_exp in self.config["experience_levels"].items():
            if current_exp >= req_exp:
                new_level = int(level)

        await interaction.response.send_message(
            f"Mission approved! {user.mention} received {sc} SC and {exp} EXP\n"
            f"Current level: {new_level}"
        )

    @app_commands.command(name="level", description="Check your or another user's level")
    async def level_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        user_id = str(target.id)
        
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
            self.save_data()
        
        exp = self.data["users"][user_id]["exp"]
        level = 1
        for lvl, req_exp in self.config["experience_levels"].items():
            if exp >= req_exp:
                level = int(lvl)
        
        next_level = min(level + 1, max(map(int, self.config["experience_levels"].keys())))
        exp_needed = self.config["experience_levels"][str(next_level)] - exp

        name_part = "Your" if user is None else f"{target.name}'s"
        await interaction.response.send_message(
            f"{name_part} Stats:\n"
            f"Level: {level}\n"
            f"EXP: {exp}\n"
            f"Next level in: {exp_needed} EXP"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
