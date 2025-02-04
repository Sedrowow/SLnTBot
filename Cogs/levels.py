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

    def get_user_priority(self, member: discord.Member) -> int:
        highest_priority = float('inf')  # Default to lowest priority
        for role in member.roles:
            role_id = str(role.id)
            if role_id in self.data.get("roles", {}):
                priority = self.data["roles"][role_id]["priority"]
                highest_priority = min(highest_priority, priority)
        return highest_priority

    def can_approve(self, approver: discord.Member, target: discord.Member) -> bool:
        approver_priority = self.get_user_priority(approver)
        target_priority = self.get_user_priority(target)
        
        # Priority 0 can approve anyone including themselves
        if approver_priority == 0:
            return True
            
        # Priority 1 and 2 can approve lower ranks but not themselves
        if approver_priority in [1, 2]:
            return target_priority > approver_priority
            
        # Other priorities cannot approve
        return False

    @commands.command(name="approve")
    @commands.has_role("Manager")
    async def approve_mission(self, ctx, user: discord.Member, mission_id: str, sc: int, exp: int):
        if not self.can_approve(ctx.author, user):
            await ctx.send("You don't have permission to approve this user's missions!")
            return

        user_id = str(user.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}
        
        self.data["users"][user_id]["sc"] += sc
        self.data["users"][user_id]["exp"] += exp
        self.save_data()

        await ctx.send(f"Mission approved! {user.mention} received {sc} SC and {exp} EXP")

    @app_commands.command(name="approve", description="Approve a mission and award SC/EXP")
    async def approve_slash(self, interaction: discord.Interaction, user: discord.Member, mission_id: str, sc: int, exp: int):
        """Approve a mission and award SC/EXP"""
        try:
            # Check if user has permission to approve
            if not self.can_approve(interaction.user, user):
                await interaction.response.send_message(
                    "You don't have permission to approve this user's missions! "
                    "You need a higher rank to approve their missions.",
                    ephemeral=True
                )
                return

            # Initialize user data if not exists
            user_id = str(user.id)
            if user_id not in self.data["users"]:
                self.data["users"][user_id] = {"sc": 0, "exp": 0}

            # Award SC and EXP
            self.data["users"][user_id]["sc"] += sc
            self.data["users"][user_id]["exp"] += exp
            self.save_data()

            # Calculate new level
            current_exp = self.data["users"][user_id]["exp"]
            new_level = 0
            for level, req_exp in sorted(self.config["experience_levels"].items(), key=lambda x: int(x[0])):
                if current_exp >= req_exp:
                    new_level = int(level)

            await interaction.response.send_message(
                f"Mission {mission_id} approved!\n"
                f"{user.mention} received {sc} SC and {exp} EXP\n"
                f"Current level: {new_level}"
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Error approving mission: {str(e)}",
                ephemeral=True
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
