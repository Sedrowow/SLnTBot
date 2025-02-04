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
            end_time = datetime.datetime.now()
            start_time = datetime.datetime.fromisoformat(self.mission_data["start_time"])
            duration = end_time - start_time
            
            class EndMissionModal(Modal):
                def __init__(self):
                    super().__init__(title="Mission End Details")
                    self.screenshot = TextInput(
                        label="Screenshot URL",
                        required=False,
                        placeholder="Paste screenshot URL here..."
                    )
                    self.reason = TextInput(
                        label="End Reason",
                        required=True,
                        placeholder="Why is the mission ending?"
                    )
                    self.add_item(self.screenshot)
                    self.add_item(self.reason)

            modal = EndMissionModal()
            await interaction.response.send_modal(modal)

            try:
                modal_inter = await self.bot.wait_for(
                    "modal_submit",
                    timeout=300.0,
                    check=lambda i: i.user.id == interaction.user.id
                )

                self.mission_data.update({
                    "status": "completed",
                    "end_time": end_time.isoformat(),
                    "duration": str(duration),
                    "end_reason": modal.reason.value,
                    "screenshot": modal.screenshot.value if modal.screenshot.value else None
                })

                # Create completion embed
                embed = discord.Embed(
                    title=f"Mission {self.mission_data['id']} Completed",
                    description=(
                        f"Duration: {duration}\n"
                        f"Category: {self.mission_data['category']}\n"
                        f"Description: {self.mission_data['description']}\n"
                        f"Reason: {modal.reason.value}"
                    ),
                    color=discord.Color.yellow()
                )

                # Handle screenshot if provided
                if modal.screenshot.value:
                    screenshots_channel_id = self.mission_data["channels"].get("screenshots")
                    if screenshots_channel_id:
                        try:
                            screenshots_channel = await self.bot.fetch_channel(int(screenshots_channel_id))
                            await screenshots_channel.send(
                                f"Screenshot for Mission #{self.mission_data['id']}\n"
                                f"Submitted by: {interaction.user.mention}\n"
                                f"URL: {modal.screenshot.value}"
                            )
                        except discord.NotFound:
                            await modal_inter.response.send_message(
                                "Warning: Could not post screenshot to screenshots channel.",
                                ephemeral=True
                            )

                # Update message
                await interaction.message.edit(embed=embed, view=None)
                await modal_inter.response.send_message("Mission completed successfully!", ephemeral=True)

            except asyncio.TimeoutError:
                await interaction.followup.send("Mission end timed out.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Error ending mission: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Abort Mission", style=discord.ButtonStyle.red)
    async def abort_mission(self, interaction: discord.Interaction, button: Button):
        verification_code = ''.join(random.choices('0123456789', k=4))
        abort_modal = AbortModal(verification_code)
        
        await interaction.response.send_modal(abort_modal)
        try:
            modal_interaction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.user.id == interaction.user.id,
                timeout=60.0
            )
            
            if await abort_modal.on_submit(modal_interaction):
                self.mission_data["status"] = "aborted"
                self.mission_data["abort_time"] = datetime.datetime.now().isoformat()
                
                # Post to mission logs
                log_channel = self.bot.get_channel(int(self.mission_data["channels"]["mission_logs"]))
                await log_channel.send(
                    embed=discord.Embed(
                        title=f"Mission {self.mission_data['id']} Aborted",
                        description=f"Category: {self.mission_data['category']}\nDescription: {self.mission_data['description']}",
                        color=discord.Color.yellow()
                    )
                )
                
                await interaction.edit_original_response(content="Mission aborted.", view=None)
        except TimeoutError:
            await interaction.followup.send("Abort confirmation timed out.", ephemeral=True)

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

async def setup(bot: commands.Bot):
    await bot.add_cog(MissionCog(bot))
