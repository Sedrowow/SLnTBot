import discord
from discord.ext import commands
from discord import app_commands
from random import randint

class HelpCog(commands.Cog, name="help command"):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.command(name = 'help',
                    usage="(commandName)",
                    description = "Display the help message.",
                    aliases = ['h', '?'])
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def help (self, ctx, commandName:str=None):

        commandName2 = None
        stop = False

        if commandName is not None:
            for i in self.bot.commands:
                if i.name == commandName.lower():
                    commandName2 = i
                    break 
                else:
                    for j in i.aliases:
                        if j == commandName.lower():
                            commandName2 = i
                            stop = True
                            break
                        if stop is True:
                            break 

            if commandName2 is None:
                await ctx.channel.send("No command found!")   
            else:
                embed = discord.Embed(title=f"{commandName2.name.upper()} Command", description="", color=randint(0, 0xffffff))
                embed.set_thumbnail(url=f'{self.bot.user.display_avatar.url}')
                embed.add_field(name=f"Name", value=f"{commandName2.name}", inline=False)
                aliases = commandName2.aliases
                aliasList = ""
                if len(aliases) > 0:
                    for alias in aliases:
                        aliasList += alias + ", "
                    aliasList = aliasList[:-2]
                    embed.add_field(name=f"Aliases", value=aliasList)
                else:
                    embed.add_field(name=f"Aliases", value="None", inline=False)

                if commandName2.usage is None:
                    embed.add_field(name=f"Usage", value=f"None", inline=False)
                else:
                    embed.add_field(name=f"Usage", value=f"{self.bot.command_prefix}{commandName2.name} {commandName2.usage}", inline=False)
                embed.add_field(name=f"Description", value=f"{commandName2.description}", inline=False)
                await ctx.channel.send(embed=embed)             
        else:
            embed = discord.Embed(title=f"Help page", description=f"{self.bot.command_prefix}help (commandName), display the help list or the help data for a specific command.", color=randint(0, 0xffffff))
            embed.set_thumbnail(url=f'{self.bot.user.display_avatar.url}')
            for i in self.bot.commands:
                embed.add_field(name=i.name, value=i.description, inline=False)
            await ctx.channel.send(embed=embed)

    @app_commands.command(name="help", description="Display the help message")
    async def help_slash(self, interaction: discord.Interaction, command_name: str = None):
        """Slash command version of help"""
        if command_name is None:
            embed = discord.Embed(
                title="Help page", 
                description="Available commands (use / or s! prefix):", 
                color=randint(0, 0xffffff)
            )
            # Add application commands
            for cmd in self.bot.tree.get_commands():
                embed.add_field(name=f"/{cmd.name}", value=cmd.description, inline=False)
            # Add prefix commands
            for cmd in self.bot.commands:
                embed.add_field(name=f"s!{cmd.name}", value=cmd.description, inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            # ... existing command-specific help logic ...
            pass

async def setup(bot:commands.Bot):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))
