from utility import *
from discord.ext import commands
import discord

class Generic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.greyple()

    @commands.command(aliases=['hello'])
    async def hi(self, ctx):
        """It's nice to just say hi sometimes."""
        name = ctx.message.author.name
        greetings = [
            "Hey, hope you're doing well today",
            "Sup {}".format(name),
            "Hi! Tell me to do something, I'm bored",
            "Ay, is there anything you want to do?",
            "Hello world! and also {}!".format(name),
            ":wave:"
        ]
        return await ctx.send(choice(greetings))
        

    @commands.command(aliases=['pong'])
    async def ping(self, ctx):
        """Pong! Shows latency."""
        return await ctx.send('Pong! Latency: `{}`'.format(round(self.bot.latency, 1)))


    @commands.command(aliases=['info'])
    async def about(self, ctx):
        """
        All about me!
        Shows the amount of servers I am in and links to my source and creator.
        """
        embed = discord.Embed(
            color=discord.Color.blurple(),
            description='\n'.join([
                ":shield: Serving {} servers".format(len(self.bot.guilds)),
                ":cat: [GitHub](https://github.com/Milotrince/discord-roombot) Help improve me!",
                ":mailbox: [Invite Link](https://discordapp.com/oauth2/authorize?client_id=592816310656696341&permissions=268437520&scope=bot) Invite me to another server!",
                ":woman: [GitHub Profile](https://github.com/Milotrince) Contact my creator @Milotrince#0001",
                ":heart: RoomBot was made for Discord Hack Week"]) )
        embed.set_author(name="About RoomBot")
        return await ctx.send(embed=embed)


    @commands.command(aliases=['commands'])
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
                    title="{} Command".format(command.cog_name) )
                embed.add_field(
                    name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
                    value=command.help,
                    inline=False )
                await ctx.send(embed=embed)
            return

        for cog_name, cog in self.bot.cogs.items():
            embed = discord.Embed(
                color=cog.color,
                title="{} Commands".format(cog_name) )
            for command in sorted(cog.get_commands(), key=lambda c:c.name):
                embed.add_field(
                    name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
                    value=command.short_doc,
                    inline=False )
            await ctx.send(embed=embed)


