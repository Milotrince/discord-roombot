from room import *
from discord.ext import commands
import discord

class Generic(commands.Cog, name=strings['_cog']['generic']):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.greyple()
        
    @commands.command(aliases=strings['_aliases']['ping'])
    async def ping(self, ctx):
        """Pong! Shows latency."""
        return await ctx.send(strings['ping'].format(round(self.bot.latency, 1)))

    @commands.command(aliases=strings['_aliases']['about'])
    async def about(self, ctx):
        """
        All about me!
        Shows the amount of servers I am in and links to my source and creator.
        """
        embed = discord.Embed(
            color=discord.Color.blurple(),
            description='\n'.join([
                ":shield: Serving {} servers".format(len(self.bot.guilds)),
                ":robot: [Server](https://discord.gg/37kzrpr) Join my support server!",
                ":cat: [GitHub](https://github.com/Milotrince/discord-roombot) Help improve me!",
                ":mailbox: [Invite Link](https://discordapp.com/oauth2/authorize?client_id=592816310656696341&permissions=268437520&scope=bot) Invite me to another server!",
                ":woman: [Profile](https://github.com/Milotrince) Contact my creator @Milotrince#0001",
                ":heart: RoomBot was made for Discord Hack Week"]) )
        embed.set_author(name="About RoomBot")
        return await ctx.send(embed=embed)

    @commands.command(aliases=strings['_aliases']['support'])
    async def support(self, ctx):
        return await ctx.send(strings['support'])

    @commands.command(aliases=strings['_aliases']['help'])
    async def help(self, ctx, *args):
        """
        Shows descriptions of all or specific commands.
        ...Like this. Pretty meta.
        """
        filtered_commands = []
        for arg in args:
            for c in self.bot.commands:
                if (c.name == arg or arg in c.aliases) and c not in filtered_commands:
                    filtered_commands.append(c)
        if len(filtered_commands) > 0:
            for command in filtered_commands:
                embed = discord.Embed(
                    color=self.bot.cogs[command.cog_name].color,
                    title="{} {}".format(command.cog_name, strings['command']) )
                embed.add_field(
                    name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
                    value=command.help,
                    inline=False )
                await ctx.send(embed=embed)
            return

        for cog_name, cog in self.bot.cogs.items():
            embed = discord.Embed(
                color=cog.color,
                title="{} {}".format(cog_name, strings['commands']) )
            for command in sorted(cog.get_commands(), key=lambda c:c.name):
                embed.add_field(
                    name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
                    value=command.short_doc,
                    inline=False )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Generic(bot))