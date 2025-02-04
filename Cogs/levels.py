import discord
from discord.ext import commands
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

def setup(bot: commands.Bot):
    bot.add_cog(LevelsCog(bot))
