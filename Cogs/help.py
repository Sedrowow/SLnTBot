import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
from random import randint

class CategorySelect(Select):
    def __init__(self, categories):
        options = [
            discord.SelectOption(
                label=category,
                description=f"View commands in {category}"
            ) for category in categories
        ]
        super().__init__(placeholder="Select a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = create_category_embed(self.view.bot, self.values[0])
        await interaction.response.edit_message(embed=embed)

class HelpView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        # Get unique categories from cogs
        categories = set(cog.qualified_name for cog in bot.cogs.values())
        self.add_item(CategorySelect(categories))

def create_category_embed(bot: commands.Bot, category: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"{category} Commands", 
        description=f"Available commands in {category}:", 
        color=randint(0, 0xffffff)
    )
    
    cog = bot.get_cog(category)
    if cog:
        for command in cog.get_app_commands():
            embed.add_field(
                name=f"/{command.name}", 
                value=command.description or "No description available",
                inline=False
            )
    return embed

def create_command_embed(command: app_commands.Command) -> discord.Embed:
    embed = discord.Embed(
        title=f"/{command.name}",
        description=command.description or "No description available",
        color=randint(0, 0xffffff)
    )
    
    # Add parameters if they exist
    if command.parameters:
        params = []
        for param in command.parameters:
            param_type = param.type.__str__().split(".")[-1]  # Get clean type name
            required = "" if param.required else " (optional)"
            params.append(f"`{param.name}`: {param_type}{required}")
        embed.add_field(name="Parameters", value="\n".join(params), inline=False)
    
    return embed

class HelpCog(commands.Cog, name="Help Command"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Display the help message")
    async def help_slash(
        self, 
        interaction: discord.Interaction, 
        category: str = None, 
        command: str = None
    ):
        if command:
            # Find and display specific command
            cmd = discord.utils.get(self.bot.tree.get_commands(), name=command.lower())
            if cmd:
                embed = create_command_embed(cmd)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "Command not found!", 
                    ephemeral=True
                )
            return

        if category:
            # Display specific category
            cog = self.bot.get_cog(category)
            if cog:
                embed = create_category_embed(self.bot, category)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "Category not found!", 
                    ephemeral=True
                )
            return

        # Display main help menu with category selection
        embed = discord.Embed(
            title="Help Menu",
            description="Select a category from the dropdown below to view commands:",
            color=randint(0, 0xffffff)
        )
        
        # Add list of categories in the embed
        categories = [cog.qualified_name for cog in self.bot.cogs.values()]
        embed.add_field(
            name="Available Categories",
            value="\n".join(f"• {cat}" for cat in categories),
            inline=False
        )
        
        view = HelpView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
