import discord
from discord.ext import commands
from discord import app_commands
import json

class LevelManageView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Add Level Role", style=discord.ButtonStyle.green)
    async def add_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = LevelRoleModal(title="Add Level Role")
        await interaction.response.send_modal(modal)
        try:
            modal_inter = await interaction.client.wait_for(
                "modal_submit",
                timeout=300.0,
                check=lambda i: i.user.id == interaction.user.id
            )
            level = int(modal.level.value)
            role_id = int(modal.role_id.value)
            
            self.cog.data["level_roles"][str(level)] = str(role_id)
            self.cog.save_data()
            await modal_inter.response.send_message(f"Added role for level {level}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

class LevelRoleModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.level = discord.ui.TextInput(
            label="Level",
            placeholder="Enter level number",
            required=True
        )
        self.role_id = discord.ui.TextInput(
            label="Role ID",
            placeholder="Enter role ID",
            required=True
        )
        self.add_item(self.level)
        self.add_item(self.role_id)

class LevelsCog(commands.Cog, name="leveling commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        with open("data/database.json", "r") as f:
            self.data = json.load(f)
            # Initialize level_roles if not exists
            if "level_roles" not in self.data:
                self.data["level_roles"] = {}
        with open("configuration.json", "r") as f:
            self.config = json.load(f)

    def save_data(self):
        with open("data/database.json", "w") as f:
            json.dump(self.data, f, indent=4)

    def get_user_priority(self, member: discord.Member) -> int:
        highest_priority = float('inf')  # Default to lowest priority
        found_role = False
        
        # Reload data to ensure we have the latest
        self.load_data()
        
        print(f"Checking roles for {member.name}...")
        print(f"Available roles in database: {self.data.get('roles', {}).keys()}")
        
        for role in member.roles:
            role_id = str(role.id)
            print(f"Checking role {role.name} (ID: {role_id})")
            if role_id in self.data.get("roles", {}):
                found_role = True
                priority = self.data["roles"][role_id]["priority"]
                print(f"Found role in system with priority {priority}")
                highest_priority = min(highest_priority, priority)
        
        final_priority = 999 if not found_role else highest_priority
        print(f"Final priority for {member.name}: {final_priority}")
        return final_priority

    def debug_roles(self, member: discord.Member) -> str:
        """Helper method to debug role priorities"""
        debug_info = []
        for role in member.roles:
            role_id = str(role.id)
            if role_id in self.data.get("roles", {}):
                priority = self.data["roles"][role_id]["priority"]
                debug_info.append(f"Role {role.name}: Priority {priority}")
            else:
                debug_info.append(f"Role {role.name}: Not in system")
        return "\n".join(debug_info)

    @app_commands.command(name="checkroles", description="Debug role priorities")
    async def check_roles(self, interaction: discord.Interaction):
        """Debug command to check role priorities"""
        debug_info = self.debug_roles(interaction.user)
        priority = self.get_user_priority(interaction.user)
        
        await interaction.response.send_message(
            f"Your role information:\n{debug_info}\n\nYour priority level: {priority}",
            ephemeral=True
        )

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

    @app_commands.command(name="levels", description="Manage level roles and settings")
    async def levels_manage(self, interaction: discord.Interaction):
        """Manage level roles and settings"""
        user_priority = self.get_user_priority(interaction.user)
        # Change condition to <= 2 instead of > 2 to allow ranks 0-2
        if user_priority <= 2:  # Ranks 0-2 can manage levels
            view = LevelManageView(self)
            embed = discord.Embed(
                title="Level Management",
                description="Current level roles:",
                color=discord.Color.blue()
            )
            
            for level, role_id in self.data.get("level_roles", {}).items():
                role = interaction.guild.get_role(int(role_id))
                embed.add_field(
                    name=f"Level {level}",
                    value=f"Role: {role.mention if role else 'Not found'}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(
                "You don't have permission to manage levels! Only ranks 0-2 can manage levels.",
                ephemeral=True
            )

    @app_commands.command(name="addexp", description="Add or remove EXP from a user")
    async def add_exp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Add or remove EXP from a user (Rank 0 only)"""
        if self.get_user_priority(interaction.user) != 0:
            await interaction.response.send_message(
                "Only highest rank can modify EXP!",
                ephemeral=True
            )
            return

        user_id = str(user.id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"sc": 0, "exp": 0}

        self.data["users"][user_id]["exp"] += amount
        if self.data["users"][user_id]["exp"] < 0:
            self.data["users"][user_id]["exp"] = 0

        self.save_data()
        await interaction.response.send_message(
            f"Updated {user.mention}'s EXP by {amount:+}. New total: {self.data['users'][user_id]['exp']}",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
