import asyncio
import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import datetime
from discord.ui import Button, View, Modal, TextInput
import random

class AbortModal(Modal):
    def __init__(self, verification_code: str):
        super().__init__(title="Mission Abort Confirmation")
        self.verification_code = verification_code
        self.code_input = TextInput(
            label="Enter verification code",
            placeholder=f"Enter the code shown above: {verification_code}",
            min_length=4,
            max_length=4
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value == self.verification_code:
            return True
        await interaction.response.send_message("Invalid code!", ephemeral=True)
        return False

class PendingMissionView(View):
    def __init__(self, bot: commands.Bot, mission_data: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.mission_data = mission_data

    @discord.ui.button(label="Start Mission", style=discord.ButtonStyle.green)
    async def start_mission(self, interaction: discord.Interaction, button: Button):
        try:
            channel = await self.bot.fetch_channel(int(self.mission_data["channels"]["missions"]))
            
            # Create active mission embed
            embed = discord.Embed(
                title=f"Mission #{self.mission_data['id']} In Progress",
                description=f"Leader: {interaction.user.mention}\nCategory: {self.mission_data['category']}\nDescription: {self.mission_data['description']}",
                color=discord.Color.green()
            )
            
            # Create active mission view with end/abort buttons
            active_view = ActiveMissionView(self.bot, self.mission_data)
            await channel.send(embed=embed, view=active_view)
            
            # Remove buttons from pending mission message
            await interaction.message.edit(view=None)
            await interaction.response.send_message("Mission started successfully!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"Error starting mission: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Request Support", style=discord.ButtonStyle.primary)
    async def request_support(self, interaction: discord.Interaction, button: Button):
        with open("data/database.json", "r") as f:
            data = json.load(f)
        
        on_duty_users = [user_id for user_id, status in data.get("duty_status", {}).items() if status["active"]]
        if not on_duty_users:
            await interaction.response.send_message("No users currently on duty!", ephemeral=True)
            return
            
        mentions = [f"<@{user_id}>" for user_id in on_duty_users]
        await interaction.response.send_message(
            f"Support requested! Pinging on-duty users:\n{' '.join(mentions)}\n"
            f"Mission #{self.mission_data['id']} needs assistance!",
            allowed_mentions=discord.AllowedMentions(users=True)
        )

class ActiveMissionView(View):
    def __init__(self, bot: commands.Bot, mission_data: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.mission_data = mission_data

    @discord.ui.button(label="End Mission", style=discord.ButtonStyle.green)
    async def end_mission(self, interaction: discord.Interaction, button: Button):
        try:
            # Get and validate screenshots channel
            screenshots_channel_id = self.mission_data["channels"].get("screenshots")
            if not screenshots_channel_id:
                await interaction.response.send_message(
                    "Error: Screenshots channel not configured! Please ask an admin to set it up.",
                    ephemeral=True
                )
                return

            try:
                screenshots_channel = await self.bot.fetch_channel(int(screenshots_channel_id))
            except (discord.NotFound, ValueError):
                await interaction.response.send_message(
                    "Error: Could not find screenshots channel! Please ask an admin to check the configuration.",
                    ephemeral=True
                )
                return

            # Send end confirmation request
            await screenshots_channel.send(
                f"Mission #{self.mission_data['id']} ending.\n"
                f"{interaction.user.mention}, please use `/confend {self.mission_data['id']} <reason>` "
                f"and optionally upload a screenshot."
            )
            
            # Update mission status
            self.mission_data["status"] = "ending"
            self.mission_data["end_initiated_by"] = interaction.user.id
            self.mission_data["end_time"] = datetime.datetime.now().isoformat()
            
            # Disable buttons
            self.clear_items()
            await interaction.message.edit(view=self)
            await interaction.response.send_message(
                "Mission end initiated. Please confirm in screenshots channel.", 
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"Error ending mission: {str(e)}", 
                ephemeral=True
            )

    @discord.ui.button(label="Abort Mission", style=discord.ButtonStyle.red)
    async def abort_mission(self, interaction: discord.Interaction, button: Button):
        try:
            # Get and validate screenshots channel
            screenshots_channel_id = self.mission_data["channels"].get("screenshots")
            if not screenshots_channel_id:
                await interaction.response.send_message(
                    "Error: Screenshots channel not configured! Please ask an admin to set it up.",
                    ephemeral=True
                )
                return

            try:
                screenshots_channel = await self.bot.fetch_channel(int(screenshots_channel_id))
            except (discord.NotFound, ValueError):
                await interaction.response.send_message(
                    "Error: Could not find screenshots channel! Please ask an admin to check the configuration.",
                    ephemeral=True
                )
                return

            # Send abort confirmation request
            await screenshots_channel.send(
                f"Mission #{self.mission_data['id']} aborting.\n"
                f"{interaction.user.mention}, please use `/confabort {self.mission_data['id']} <reason>` "
                f"and optionally upload a screenshot."
            )
            
            # Update mission status
            self.mission_data["status"] = "aborting"
            self.mission_data["abort_initiated_by"] = interaction.user.id
            self.mission_data["abort_time"] = datetime.datetime.now().isoformat()
            
            # Disable buttons
            self.clear_items()
            await interaction.message.edit(view=self)
            await interaction.response.send_message(
                "Mission abort initiated. Please confirm in screenshots channel.", 
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"Error aborting mission: {str(e)}", 
                ephemeral=True
            )
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

    async def post_to_pending_missions(self, mission_data: dict):
        try:
            # Get channel IDs from data and verify they exist
            channels = self.data.get("channels", {})
            mission_data["channels"] = {
                "missions": channels.get("missions"),
                "mission_logs": channels.get("mission_logs"),
                "pending_missions": channels.get("pending_missions"),
                "screenshots": channels.get("screenshots")
            }

            # Verify pending_missions channel exists
            channel_id = channels.get("pending_missions")
            if not channel_id:
                return False

            channel = await self.bot.fetch_channel(int(channel_id))
            if not channel:
                return False

            view = PendingMissionView(self.bot, mission_data)
            embed = discord.Embed(
                title=f"New Mission #{mission_data['id']}",
                description=f"Category: {mission_data['category']}\nDescription: {mission_data['description']}",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed, view=view)
            return True
        except (discord.NotFound, ValueError, TypeError):
            return False

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
        try:
            # Validate category
            if category.value not in self.config["mission_categories"]:
                await interaction.response.send_message(
                    "Invalid category. Available categories: " + ", ".join(self.config["mission_categories"]))
                return

            # Check if channels exist
            channels = self.data.get("channels", {})
            required_channels = {
                "missions": channels.get("missions"),
                "mission_logs": channels.get("mission_logs"),
                "pending_missions": channels.get("pending_missions")
            }

            # Verify all required channels exist and are accessible
            missing_channels = []
            for name, channel_id in required_channels.items():
                if not channel_id:
                    missing_channels.append(name)
                else:
                    try:
                        await self.bot.fetch_channel(int(channel_id))
                    except (discord.NotFound, ValueError):
                        missing_channels.append(name)

            if missing_channels:
                await interaction.response.send_message(
                    f"Error: Missing or invalid channel configuration for: {', '.join(missing_channels)}. Please set them up first.",
                    ephemeral=True
                )
                return

            # Create mission
            mission_id = str(len(self.data.get("active_missions", {})) + 1)
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

            if "active_missions" not in self.data:
                self.data["active_missions"] = {}

            self.data["active_missions"][mission_id] = mission
            self.save_data()

            # Post to pending_missions
            success = await self.post_to_pending_missions(mission)
            if success:
                await interaction.response.send_message(
                    f"Mission {mission_id} created! Check pending missions channel.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Error: Could not post to pending missions channel. Please check channel configuration.",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"Error creating mission: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="confend", description="Confirm mission end with reason and optional screenshot")
    async def confirm_end(self, interaction: discord.Interaction, mission_id: str, reason: str, screenshot_url: str = None):
        """Confirm mission end with reason and optional screenshot"""
        try:
            if mission_id not in self.data["active_missions"]:
                await interaction.response.send_message("Mission not found!", ephemeral=True)
                return

            mission = self.data["active_missions"][mission_id]
            if mission["status"] != "ending":
                await interaction.response.send_message("This mission is not in ending state!", ephemeral=True)
                return

            if interaction.user.id != mission["end_initiated_by"]:
                await interaction.response.send_message("Only the person who initiated the end can confirm it!", ephemeral=True)
                return

            # Calculate duration
            end_time = datetime.datetime.fromisoformat(mission["end_time"])
            start_time = datetime.datetime.fromisoformat(mission["start_time"])
            duration = end_time - start_time

            # Update mission data
            mission.update({
                "status": "completed",
                "end_reason": reason,
                "screenshot": screenshot_url,
                "duration": str(duration)
            })
            self.save_data()

            # Create completion embed
            embed = discord.Embed(
                title=f"Mission {mission_id} Completed",
                description=(
                    f"Duration: {duration}\n"
                    f"Category: {mission['category']}\n"
                    f"Description: {mission['description']}\n"
                    f"Reason: {reason}"
                ),
                color=discord.Color.yellow()
            )
            if screenshot_url:
                embed.add_field(name="Screenshot", value=screenshot_url)

            # Post to missions channel
            channel = await self.bot.fetch_channel(int(mission["channels"]["missions"]))
            await channel.send(embed=embed)
            
            await interaction.response.send_message("Mission end confirmed!", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error confirming mission end: {str(e)}", ephemeral=True)

    @app_commands.command(name="confabort", description="Confirm mission abort with reason and optional screenshot")
    async def confirm_abort(self, interaction: discord.Interaction, mission_id: str, reason: str, screenshot_url: str = None):
        """Confirm mission abort with reason and optional screenshot"""
        try:
            if mission_id not in self.data["active_missions"]:
                await interaction.response.send_message("Mission not found!", ephemeral=True)
                return

            mission = self.data["active_missions"][mission_id]
            if mission["status"] != "aborting":
                await interaction.response.send_message("This mission is not in aborting state!", ephemeral=True)
                return

            if interaction.user.id != mission["abort_initiated_by"]:
                await interaction.response.send_message("Only the person who initiated the abort can confirm it!", ephemeral=True)
                return

            # Update mission data
            mission["status"] = "aborted"
            mission["abort_reason"] = reason
            mission["screenshot"] = screenshot_url
            self.save_data()

            # Create abort embed
            embed = discord.Embed(
                title=f"Mission {mission_id} Aborted",
                description=(
                    f"Category: {mission['category']}\n"
                    f"Description: {mission['description']}\n"
                    f"Reason: {reason}"
                ),
                color=discord.Color.red()
            )
            if screenshot_url:
                embed.add_field(name="Screenshot", value=screenshot_url)

            # Post to mission logs
            log_channel = await self.bot.fetch_channel(int(mission["channels"]["mission_logs"]))
            await log_channel.send(embed=embed)
            
            await interaction.response.send_message("Mission abort confirmed!", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error confirming mission abort: {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(MissionCog(bot))
