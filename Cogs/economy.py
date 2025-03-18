import discord
from discord.ext import commands
import json
from discord import app_commands

class EconomyCog(commands.Cog, name="Economy"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)
            print(f"Loaded data: {self.data}")  # Debugging line

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    @app_commands.command(name="balance", description="Check your SC balance")
    async def balance_slash(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
            self.save_data()
        
        balance = self.data["users"][user_id]["sc"]
        print(f"User ID: {user_id}, Balance: {balance}")  # Debugging line
        await interaction.response.send_message(f"Your balance: {balance} SC")

    @app_commands.command(name="transfer", description="Transfer SC to another user")
    async def transfer_slash(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive!", ephemeral=True)
            return

        sender_id = str(interaction.user.id)
        recipient_id = str(recipient.id)

        # Initialize user data if not exists
        for user_id in [sender_id, recipient_id]:
            if user_id not in self.data["users"]:
                self.data["users"][user_id] = {"sc": 0, "exp": 0}

        # Check if sender has enough SC
        if self.data["users"][sender_id]["sc"] < amount:
            await interaction.response.send_message("Insufficient balance!", ephemeral=True)
            return

        # Perform transfer
        self.data["users"][sender_id]["sc"] -= amount
        self.data["users"][recipient_id]["sc"] += amount
        self.save_data()

        await interaction.response.send_message(
            f"Successfully transferred {amount} SC to {recipient.mention}"
        )

    # New command to modify a user's balance
    @app_commands.command(name="modifybalance", description="Modify a user's SC balance")
    @app_commands.checks.has_permissions(administrator=True)
    async def modify_balance_slash(self, interaction: discord.Interaction, user: discord.Member, new_balance: int):
        user_id = str(user.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
        
        self.data["users"][user_id]["sc"] = new_balance
        self.save_data()
        
        await interaction.response.send_message(
            f"The balance of {user.mention} has been set to {new_balance} SC."
        )

    @modify_balance_slash.error
    async def modify_balance_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))