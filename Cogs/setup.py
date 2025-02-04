import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View, Button
import json

class RoleSelect(Select):
    def __init__(self, roles):
        options = [
            discord.SelectOption(label=role["name"], value=role["id"])
            for role in roles
        ]
        super().__init__(placeholder="Select a role", options=options)

class SetupSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Choose setup type",
            options=[
                discord.SelectOption(label="Role Setup", value="role"),
                discord.SelectOption(label="Channel Setup", value="channel")
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "role":
            await interaction.response.send_message("Role setup selected. Use `/role` or `s!role` to manage roles.")
        else:
            await interaction.response.send_message("Channel setup selected. Use `/channel` or `s!channel` to manage channels.")

class SetupView(View):
    def __init__(self):
        super().__init__()
        self.add_item(SetupSelect())

class SetupCog(commands.Cog, name="setup commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_prefix(self, ctx):
        """Traditional prefix command for setup"""
        view = SetupView()
        await ctx.send("Please select what you want to set up:", view=view)

    @app_commands.command(name="setup", description="Set up roles and channels for the bot")
    @app_commands.default_permissions(administrator=True)
    async def setup_slash(self, interaction: discord.Interaction):
        """Slash command for setup"""
        view = SetupView()
        await interaction.response.send_message("Please select what you want to set up:", view=view)

    @commands.command(name="role")
    @commands.has_permissions(administrator=True)
    async def role(self, ctx, role_name: str, priority: int):
        """Add a new role to the ranking system"""
        # Create the role if it doesn't exist
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            role = await ctx.guild.create_role(name=role_name)

        role_data = {
            "id": str(role.id),
            "name": role_name,
            "priority": priority,
            "bonus_income": 1.0  # 1% default bonus
        }

        self.data["roles"][str(role.id)] = role_data
        self.save_data()
        await ctx.send(f"Role {role_name} added with priority {priority}")

    @app_commands.command(name="role", description="Add a new role to the ranking system")
    @app_commands.default_permissions(administrator=True)
    async def role_slash(self, interaction: discord.Interaction, role_name: str, priority: int):
        """Slash command version of role command"""
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            role = await interaction.guild.create_role(name=role_name)

        role_data = {
            "id": str(role.id),
            "name": role_name,
            "priority": priority,
            "bonus_income": 1.0
        }

        self.data["roles"][str(role.id)] = role_data
        self.save_data()
        await interaction.response.send_message(f"Role {role_name} added with priority {priority}")

    @commands.command(name="editrole")
    @commands.has_permissions(administrator=True)
    async def edit_role(self, ctx, role: discord.Role, field: str, value: str):
        """Edit a role's properties (name/priority/bonus)"""
        role_id = str(role.id)
        if role_id not in self.data["roles"]:
            await ctx.send("This role is not in the ranking system!")
            return

        if field not in ["name", "priority", "bonus_income"]:
            await ctx.send("Invalid field! Use: name, priority, or bonus_income")
            return

        if field == "priority":
            value = int(value)
        elif field == "bonus_income":
            value = float(value)

        self.data["roles"][role_id][field] = value
        self.save_data()
        await ctx.send(f"Updated {field} for role {role.name}")

    @commands.command(name="removerole")
    @commands.has_permissions(administrator=True)
    async def remove_role(self, ctx, role: discord.Role):
        """Remove a role from the ranking system"""
        role_id = str(role.id)
        if role_id in self.data["roles"]:
            del self.data["roles"][role_id]
            self.save_data()
            await ctx.send(f"Role {role.name} removed from ranking system")
        else:
            await ctx.send("This role is not in the ranking system!")

    # Add error handlers for invalid commands
    @setup_prefix.error
    async def setup_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Setup command not found. Use `/setup` or `s!setup`")

async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
