import discord
from discord.ext import commands
import json

class EconomyCog(commands.Cog, name="economy commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    @commands.command(name="balance")
    async def balance(self, ctx):
        user_id = str(ctx.author.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
            self.save_data()
        
        balance = self.data["users"][user_id]["sc"]
        await ctx.send(f"Your balance: {balance} SC")

def setup(bot: commands.Bot):
    bot.add_cog(EconomyCog(bot))
