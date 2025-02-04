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

class ChannelSelect(Select):
    def __init__(self, channels, purpose):
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in channels if isinstance(channel, discord.TextChannel)
        ][:25]  # Discord has a 25 option limit
        super().__init__(placeholder=f"Select {purpose} channel", options=options)
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if isinstance(view, ChannelSetupView):
            await view.set_channel(interaction, self.values[0], self.purpose)

class ChannelSetupView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        
    async def set_channel(self, interaction, channel_id, purpose):
        with open("data/database.json", "r") as f:
            data = json.load(f)
        
        if "channels" not in data:
            data["channels"] = {}
            
        data["channels"][purpose] = str(channel_id)
        
        with open("data/database.json", "w") as f:
            json.dump(data, f, indent=4)
        
        await interaction.response.send_message(f"Set <#{channel_id}> as the {purpose} channel", ephemeral=True)

class SetupView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        setup_select = Select(
            placeholder="Choose setup type",
            options=[
                discord.SelectOption(label="Role Setup", value="role"),
                discord.SelectOption(label="Channel Setup", value="channel")
            ]
        )

        async def setup_callback(interaction: discord.Interaction):
            if setup_select.values[0] == "role":
                await interaction.response.send_message("Role setup selected. Use `/role` or `s!role` to manage roles.")
            else:
                view = ChannelSetupView(self.bot)
                for purpose in ["missions", "announcements", "pending_missions", "mission_logs"]:
                    view.add_item(ChannelSelect(interaction.guild.channels, purpose))
                await interaction.response.send_message("Select channels to configure:", view=view)

        setup_select.callback = setup_callback
        self.add_item(setup_select)

class SetupCog(commands.Cog, name="setup commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)
            # Initialize required structures if they don't exist
            if "roles" not in self.data:
                self.data["roles"] = {}
            self.save_data()

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_prefix(self, ctx):
        """Traditional prefix command for setup"""
        view = SetupView(self.bot)
        await ctx.send("Please select what you want to set up:", view=view)

    @app_commands.command(name="setup", description="Set up roles and channels for the bot")
    @app_commands.default_permissions(administrator=True)
    async def setup_slash(self, interaction: discord.Interaction):
        """Slash command for setup"""
        view = SetupView(self.bot)
        await interaction.response.send_message("Please select what you want to set up:", view=view)

    @commands.command(name="role")
    @commands.has_permissions(administrator=True)
    async def role(self, ctx, role: discord.Role, priority: int):
        """Add an existing role to the ranking system"""
        if str(role.id) in self.data["roles"]:
            await ctx.send(f"Role {role.name} is already in the ranking system! Use /editrole to modify it.")
            return

        role_data = {
            "id": str(role.id),
            "name": role.name,
            "priority": priority,
            "bonus_income": 1.0
        }

        self.data["roles"][str(role.id)] = role_data
        self.save_data()
        await ctx.send(f"Added existing role {role.mention} to ranking system with priority {priority}")

    @app_commands.command(name="role", description="Add an existing role to the ranking system")
    @app_commands.default_permissions(administrator=True)
    async def role_slash(self, interaction: discord.Interaction, role: discord.Role, priority: int):
        """Add an existing role to the ranking system"""
        try:
            role_data = {
                "id": str(role.id),
                "name": role.name,
                "priority": priority,
                "bonus_income": 1.0
            }

            if "roles" not in self.data:
                self.data["roles"] = {}
            
            if str(role.id) in self.data["roles"]:
                await interaction.response.send_message(
                    f"Role {role.name} is already in the ranking system! Use /editrole to modify it.",
                    ephemeral=True
                )
                return
            
            self.data["roles"][str(role.id)] = role_data
            self.save_data()
            
            await interaction.response.send_message(
                f"Added existing role {role.mention} to ranking system with priority {priority}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error adding role: {str(e)}",
                ephemeral=True
            )

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

    @app_commands.command(name="setchannel", description="Set a channel for a specific purpose")
    @app_commands.choices(purpose=[
        app_commands.Choice(name="Missions", value="missions"),
        app_commands.Choice(name="Announcements", value="announcements"),
        app_commands.Choice(name="Pending Missions", value="pending_missions"),
        app_commands.Choice(name="Mission Logs", value="mission_logs"),
        app_commands.Choice(name="Screenshots", value="screenshots")  # Added screenshots channel
    ])
    @app_commands.default_permissions(administrator=True)
    async def setchannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel, purpose: app_commands.Choice[str]):
        """Set a channel for a specific purpose"""
        try:
            if "channels" not in self.data:
                self.data["channels"] = {}
            
            self.data["channels"][purpose.value] = str(channel.id)
            self.save_data()
            
            await interaction.response.send_message(
                f"Set {channel.mention} as the {purpose.name} channel",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error setting channel: {str(e)}",
                ephemeral=True
            )

    # Add error handlers for invalid commands
    @setup_prefix.error
    async def setup_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Setup command not found. Use `/setup` or `s!setup`")

async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
