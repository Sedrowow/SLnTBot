import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import datetime
import random
import asyncio

class DutyCog(commands.Cog, name="Duty System"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()
        self.check_duty_status.start()
        self.confirmation_codes = {}

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)
        if "duty_status" not in self.data:
            self.data["duty_status"] = {}

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    def calculate_duty_reward(self, user_id: str, duration_minutes: float) -> tuple[int, int]:
        user_data = self.data["users"].get(str(user_id), {"level": 0})
        base_reward = 10  # Base SC per 30 minutes
        
        # Level multipliers
        level_multipliers = {
            0: 1.0,  # Normal income
            1: 1.5,  # 15 SC per 30 minutes
            # Add more levels as needed
        }
        
        multiplier = level_multipliers.get(user_data.get("level", 0), 1.0)
        bonus_percent = self.data.get("bonus_income", {}).get(str(user_id), 0)
        
        base_amount = (base_reward * multiplier * duration_minutes) / 30
        bonus_amount = base_amount * (bonus_percent / 100)
        
        return int(base_amount + bonus_amount), int(base_amount * 0.5)  # SC and EXP

    @tasks.loop(minutes=30)
    async def check_duty_status(self):
        for user_id, status in self.data["duty_status"].items():
            if status["active"]:
                code = ''.join(random.choices('0123456789', k=4))
                self.confirmation_codes[user_id] = code
                
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    await user.send(f"Still on duty? Enter `/confirm {code}` within 5 minutes to stay on duty.")
                    
                    await asyncio.sleep(300)  # Wait 5 minutes
                    
                    if user_id in self.confirmation_codes:  # If code wasn't confirmed
                        await self.set_off_duty(user_id)
                        await user.send("You have been automatically set to off duty.")
                except:
                    continue

    @app_commands.command(name="onduty", description="Set yourself as on duty")
    async def on_duty(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        self.data["duty_status"][user_id] = {
            "active": True,
            "start_time": datetime.datetime.now().isoformat()
        }
        self.save_data()
        await interaction.response.send_message("You are now on duty!", ephemeral=True)

    @app_commands.command(name="offduty", description="Set yourself as off duty")
    async def off_duty(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        await self.set_off_duty(user_id)
        await interaction.response.send_message("You are now off duty!", ephemeral=True)

    @app_commands.command(name="confirm", description="Confirm you're still on duty")
    async def confirm_duty(self, interaction: discord.Interaction, code: str):
        user_id = str(interaction.user.id)
        if user_id in self.confirmation_codes:
            if code == self.confirmation_codes[user_id]:
                del self.confirmation_codes[user_id]
                await interaction.response.send_message("Duty status confirmed!", ephemeral=True)
            else:
                await interaction.response.send_message("Invalid code!", ephemeral=True)
        else:
            await interaction.response.send_message("No confirmation needed at this time.", ephemeral=True)

    async def set_off_duty(self, user_id: str):
        if user_id in self.data["duty_status"]:
            status = self.data["duty_status"][user_id]
            if status["active"]:
                end_time = datetime.datetime.now()
                start_time = datetime.datetime.fromisoformat(status["start_time"])
                duration = (end_time - start_time).total_seconds() / 60  # Duration in minutes
                
                sc_reward, exp_reward = self.calculate_duty_reward(user_id, duration)
                
                if user_id not in self.data["users"]:
                    self.data["users"][user_id] = {"sc": 0, "exp": 0}
                
                self.data["users"][user_id]["sc"] += sc_reward
                self.data["users"][user_id]["exp"] += exp_reward
                status["active"] = False
                self.save_data()

async def setup(bot: commands.Bot):
    await bot.add_cog(DutyCog(bot))
