from database.room import *
from discord.ext import commands
import discord

class Generic(commands.Cog, name=get_text('_cog')['generic']):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.greyple()
        
    @commands.command()
    async def ping(self, ctx):
        """Pong! Shows latency."""
        m = await ctx.send(get_text('ping'))
        ms = (m.created_at-ctx.message.created_at).total_seconds() * 1000
        await m.edit(content=get_text('pong').format(int(ms)))
        # return await ctx.send(get_text('ping').format(round(self.bot.latency, 1)))

    @commands.command()
    async def donate(self, ctx):
        embed = discord.Embed(
            color=discord.Color.blurple(),
            title=":heart: Support me through Ko-fi! :coffee:",
            description="https://ko-fi.com/milotrince\nDonations help me stay motivated to continue updating and managing RoomBot, as well as pay hosting fees. So if RoomBot helps you out, please consider helping me out too! :blush:",
            url="https://ko-fi.com/milotrince"
        ).set_author(
            name="Donate"
        ).set_thumbnail(
            url="https://storage.ko-fi.com/cdn/useruploads/6d456b7f-ed0f-4690-942a-8f2153e31602.png"
        )
        return await ctx.send(embed=embed)



    @commands.command()
    async def about(self, ctx):
        """
        All about me!
        Shows the amount of servers I am in and links to my source and creator.
        """
        embed = discord.Embed(
            color=discord.Color.blurple(),
            title="About Roombot",
            description='\n'.join([
                ":shield: Serving {} servers".format(len(self.bot.guilds)),
                ":robot: [Server](https://discord.gg/37kzrpr) Join my support server!",
                ":cat: [GitHub](https://github.com/Milotrince/discord-roombot) Help improve me!",
                ":mailbox: [Invite Link](https://discordapp.com/oauth2/authorize?client_id=592816310656696341&permissions=268437520&scope=bot) Invite me to another server!",
                ":woman: [Profile](https://github.com/Milotrince) Contact my creator @Milotrince#0001",
                ":heart: [Ko-fi](https://ko-fi.com/milotrince) Donate :coffee:!",
                ":purple_heart: RoomBot was made for Discord Hack Week"])
            ).set_thumbnail(
                url="https://raw.githubusercontent.com/Milotrince/discord-roombot/master/assets/icon.png"
            )
        return await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx):
        return await ctx.send(get_text('support'))

    @commands.command()
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
                    title="{} {}".format(command.cog_name, get_text('command')) )
                embed.add_field(
                    name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
                    value=command.help,
                    inline=False )
                await ctx.send(embed=embed)
            return

        for cog_name, cog in self.bot.cogs.items():
            embed = discord.Embed(
                color=cog.color,
                title="{} {}".format(cog_name, get_text('commands')) )
            for command in sorted(cog.get_commands(), key=lambda c:c.name):
                embed.add_field(
                    name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
                    value=command.short_doc,
                    inline=False )
            await ctx.send(embed=embed)


def setup(bot):
    load_cog(bot, Generic(bot))