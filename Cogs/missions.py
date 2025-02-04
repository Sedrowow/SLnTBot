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

class MissionView(View):
    def __init__(self, bot: commands.Bot, mission_data: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.mission_data = mission_data

    @discord.ui.button(label="End Mission", style=discord.ButtonStyle.green)
    async def end_mission(self, interaction: discord.Interaction, button: Button):
        end_time = datetime.datetime.now()
        start_time = datetime.datetime.fromisoformat(self.mission_data["start_time"])
        duration = end_time - start_time
        
        self.mission_data["end_time"] = end_time.isoformat()
        self.mission_data["duration"] = str(duration)
        self.mission_data["status"] = "completed"
        
        # Create screenshot request modal
        screenshot_modal = Modal(title="Add Screenshot")
        screenshot_input = TextInput(
            label="Screenshot URL (optional)",
            required=False,
            placeholder="Paste screenshot URL here"
        )
        screenshot_modal.add_item(screenshot_input)
        await interaction.response.send_modal(screenshot_modal)
        
        # Wait for modal response
        try:
            modal_interaction = await self.bot.wait_for(
                "modal_submit",
                timeout=300.0
            )
            if screenshot_input.value:
                self.mission_data["screenshot"] = screenshot_input.value
        except TimeoutError:
            pass

        # Post to missions channel
        missions_channel_id = self.bot.get_channel(int(self.mission_data["channels"]["missions"]))
        await missions_channel_id.send(
            embed=discord.Embed(
                title=f"Mission {self.mission_data['id']} Completed",
                description=f"Duration: {duration}\nCategory: {self.mission_data['category']}\nDescription: {self.mission_data['description']}",
                color=discord.Color.blue()
            )
        )

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
        channel_id = self.data["channels"].get("pending_missions")
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                view = MissionView(self.bot, mission_data)
                await channel.send(
                    embed=discord.Embed(
                        title=f"New Mission #{mission_data['id']}",
                        description=f"Category: {mission_data['category']}\nDescription: {mission_data['description']}",
                        color=discord.Color.blue()
                    ),
                    view=view
                )

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

        await self.post_to_pending_missions(mission)
        await interaction.response.send_message(f"Mission {mission_id} created and posted to pending missions!")

async def setup(bot: commands.Bot):
    await bot.add_cog(MissionCog(bot))
