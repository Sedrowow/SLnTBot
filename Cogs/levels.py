import discord
from discord.ext import commands
from discord import app_commands
import json

class LevelManageView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Add/Edit Level Role", style=discord.ButtonStyle.green)
    async def add_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = LevelRoleModal()
        await interaction.response.send_modal(modal)
        try:
            modal_inter = await interaction.client.wait_for(
                "modal_submit",
                timeout=300.0,
                check=lambda i: i.user.id == interaction.user.id
            )
            
            level_data = {
                "role_id": str(modal.role.value),
                "exp_required": int(modal.exp_required.value),
                "duty_income": float(modal.duty_income.value),
                "mission_bonus": float(modal.mission_bonus.value)
            }
            
            self.cog.data["level_roles"][str(modal.level.value)] = level_data
            self.cog.save_data()
            # If this is level 0, assign it to members who have a hierarchy role
            if int(modal.level.value) == 0:
                for member in interaction.guild.members:
                    if str(member.id) not in self.cog.data["users"] and any(str(role.id) in self.cog.data.get("roles", {}) for role in member.roles):
                        await self.cog.assign_default_levels(interaction.guild)
            
            await modal_inter.response.send_message(
                f"Level {modal.level.value} configured successfully!", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

class LevelRoleModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(title="Configure Level Role")
        self.level = discord.ui.TextInput(
            label="Level Number",
            placeholder="Enter level number (0 is lowest)",
            required=True
        )
        self.role = discord.ui.TextInput(
            label="Role ID",
            placeholder="Enter existing role ID",
            required=True
        )
        self.exp_required = discord.ui.TextInput(
            label="Required EXP",
            placeholder="EXP needed to reach this level",
            required=True
        )
        self.duty_income = discord.ui.TextInput(
            label="Duty Income per 30min",
            placeholder="Base income for duty time",
            required=True
        )
        self.mission_bonus = discord.ui.TextInput(
            label="Mission Bonus %",
            placeholder="Bonus percentage for missions",
            required=True
        )
        for item in [self.level, self.role, self.exp_required, self.duty_income, self.mission_bonus]:
            self.add_item(item)

class LevelsCog(commands.Cog, name="leveling commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        try:
            with open("data/database.json", "r") as f:
                self.data = json.load(f)
                print("Loaded data:", self.data)  # Debug print
                # Initialize level_roles if not exists
                if "level_roles" not in self.data:
                    self.data["level_roles"] = {}
                if "roles" not in self.data:
                    self.data["roles"] = {}
            with open("configuration.json", "r") as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.data = {"roles": {}, "level_roles": {}}

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
        # Force reload data to ensure we have latest
        self.load_data()
        
        debug_info = []
        debug_info.append(f"Database roles: {list(self.data.get('roles', {}).keys())}")
        
        for role in member.roles:
            role_id = str(role.id)
            if role_id in self.data.get("roles", {}):
                role_data = self.data["roles"][role_id]
                priority = role_data["priority"]
                debug_info.append(f"Role {role.name} (ID: {role_id}): Priority {priority}")
            else:
                debug_info.append(f"Role {role.name} (ID: {role_id}): Not in system")
        return "\n".join(debug_info)

    @app_commands.command(name="checkroles", description="Debug role priorities")
    async def check_roles(self, interaction: discord.Interaction):
        """Debug command to check role priorities"""
        debug_info = self.debug_roles(interaction.user)
        priority = self.get_user_priority(interaction.user)
        
        await interaction.response.send_message(
            f"Debug Information:\n"
            f"{debug_info}\n\n"
            f"Your calculated priority level: {priority}",
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
    @app_commands.choices(action=[
        app_commands.Choice(name="View All", value="view"),
        app_commands.Choice(name="Add/Edit Level", value="add"),
        app_commands.Choice(name="Remove Level", value="remove")
    ])
    async def levels_manage(
        self, 
        interaction: discord.Interaction, 
        action: app_commands.Choice[str],
        level: int = None,
        role: discord.Role = None,
        exp_required: int = None,
        duty_income: float = None,
        mission_bonus: float = None
    ):
        """Manage level roles and settings"""
        try:
            user_priority = self.get_user_priority(interaction.user)
            if user_priority > 2:
                await interaction.response.send_message(
                    "You don't have permission to manage levels!",
                    ephemeral=True
                )
                return

            # Show current levels if viewing
            if action.value == "view":
                embed = discord.Embed(
                    title="Level Management",
                    description="Current level configuration:",
                    color=discord.Color.blue()
                )
                
                for level, data in sorted(self.data.get("level_roles", {}).items(), key=lambda x: int(x[0])):
                    role = interaction.guild.get_role(int(data["role_id"]))
                    embed.add_field(
                        name=f"Level {level}",
                        value=(
                            f"Role: {role.mention if role else 'Not found'}\n"
                            f"Required EXP: {data['exp_required']}\n"
                            f"Duty Income: {data['duty_income']} SC/30min\n"
                            f"Mission Bonus: {data['mission_bonus']}%"
                        ),
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return

            # Handle add/edit action
            if action.value == "add":
                if not all([level is not None, role, exp_required is not None, duty_income is not None, mission_bonus is not None]):
                    await interaction.response.send_message(
                        "All parameters required for adding/editing a level!",
                        ephemeral=True
                    )
                    return

                level_data = {
                    "role_id": str(role.id),
                    "exp_required": exp_required,
                    "duty_income": duty_income,
                    "mission_bonus": mission_bonus
                }
                
                self.data["level_roles"][str(level)] = level_data
                self.save_data()

                # If this is level 0, assign it to members who have a hierarchy role
                if level == 0:
                    await self.assign_default_levels(interaction.guild)

                await interaction.response.send_message(
                    f"Level {level} configured with role {role.mention}",
                    ephemeral=True
                )

            # Handle remove action
            elif action.value == "remove":
                if level is None:
                    await interaction.response.send_message(
                        "Please specify a level to remove!",
                        ephemeral=True
                    )
                    return

                if str(level) in self.data["level_roles"]:
                    del self.data["level_roles"][str(level)]
                    self.save_data()
                    await interaction.response.send_message(
                        f"Level {level} removed from configuration",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"Level {level} not found in configuration",
                        ephemeral=True
                    )

        except Exception as e:
            await interaction.response.send_message(
                f"Error managing levels: {str(e)}",
                ephemeral=True
            )

    async def assign_default_levels(self, guild: discord.Guild):
        """Assign level 0 role to all users who don't have a level role"""
        if "0" not in self.data["level_roles"]:
            return
            
        default_role_id = self.data["level_roles"]["0"]["role_id"]
        default_role = guild.get_role(int(default_role_id))
        if not default_role:
            return

        for member in guild.members:
            user_id = str(member.id)
            if user_id not in self.data["users"]:
                self.data["users"][user_id] = {"sc": 0, "exp": 0, "level": 0}
                await member.add_roles(default_role)

    async def check_level_up(self, user_id: str, guild: discord.Guild):
        """Check and process level up for a user"""
        if user_id not in self.data["users"]:
            return

        user_data = self.data["users"][user_id]
        current_exp = user_data.get("exp", 0)
        current_level = user_data.get("level", 0)

        # Find next level
        next_level = None
        for level, data in sorted(self.data["level_roles"].items(), key=lambda x: int(x[0])):
            if int(level) > current_level and current_exp >= data["exp_required"]:
                next_level = int(level)
                break

        if next_level is not None:
            # Remove old level role
            if str(current_level) in self.data["level_roles"]:
                old_role_id = self.data["level_roles"][str(current_level)]["role_id"]
                old_role = guild.get_role(int(old_role_id))
                if old_role:
                    member = guild.get_member(int(user_id))
                    if member:
                        await member.remove_roles(old_role)

            # Add new level role
            new_role_id = self.data["level_roles"][str(next_level)]["role_id"]
            new_role = guild.get_role(int(new_role_id))
            if new_role:
                member = guild.get_member(int(user_id))
                if member:
                    await member.add_roles(new_role)
                    
            # Update user data
            self.data["users"][user_id].update({
                "level": next_level,
                "exp": 0  # Reset EXP on level up
            })
            self.save_data()
            
            return next_level
        return None

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
