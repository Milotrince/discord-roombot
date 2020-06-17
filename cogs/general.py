import discord
from discord.ext import commands
from database.room import *
from utils.pagesembed import EmbedPagesEmbed

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.greyple()
        
    @commands.command()
    async def ping(self, ctx):
        s = Settings.get_for(ctx.guild.id)
        m = await ctx.send(s.get_text('ping'))
        ms = (m.created_at-ctx.message.created_at).total_seconds() * 1000
        await m.edit(content=s.get_text('pong').format(int(ms)))

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
        embed = discord.Embed(
            color=discord.Color.blurple(),
            title="About Roombot",
            description='\n'.join([
                ":shield: Serving {} servers".format(len(self.bot.guilds)),
                ":robot: [Server](https://discord.gg/37kzrpr) Join my support server!",
                ":cat: [GitHub](https://github.com/Milotrince/discord-roombot) Help improve me!",
                ":mailbox: [Invite Link](https://discord.com/api/oauth2/authorize?client_id=592816310656696341&permissions=285224016&scope=bot) Invite me to another server!",
                ":woman: [Profile](https://github.com/Milotrince) Contact my creator @Milotrince#0001",
                ":heart: [Ko-fi](https://ko-fi.com/milotrince) Donate :coffee:!",
                ":purple_heart: RoomBot was made for Discord Hack Week"])
            ).set_thumbnail(
                url="https://raw.githubusercontent.com/Milotrince/discord-roombot/master/assets/icon.png"
            )
        return await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx):
        s = Settings.get_for(ctx.guild.id)
        return await ctx.send(s.get_text('support'))

    @commands.command()
    async def help(self, ctx, *args):
        s = Settings.get_for(ctx.guild.id)
        filtered_commands = []
        for arg in args:
            for c in self.bot.commands:
                if (c.name == arg or arg in c.aliases) and c not in filtered_commands:
                    filtered_commands.append(c)
        if len(filtered_commands) > 0:
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=s.get_text('help') )
            for command in filtered_commands:
                text = s.get_text('_commands')[command.name]
                embed.add_field(
                    name="**{}**    {} `{}`".format(text['_name'], s.get_text('alias'), "`, `".join(text['_aliases'])),
                    value='\n'.join(text['_help']),
                    inline=False )
            return await ctx.send(embed=embed)

        embeds = []
        for cog_name, cog in self.bot.cogs.items():
            cog_text = s.get_text('_cog')
            embed = discord.Embed(
                color=cog.color,
                title=s.get_text('help'),
                description='**{}**'.format(cog_text[cog_name]) )
            for command in sorted(cog.get_commands(), key=lambda c:c.name):
                text = s.get_text('_commands')[command.name]
                embed.add_field(
                    name="**{}**    {} `{}`".format(text['_name'], s.get_text('alias'), "`, `".join(text['_aliases'])),
                    value='\n'.join(text['_help']),
                    inline=False )
            embeds.append(embed)
        timed_out_embed = discord.Embed(
            color=discord.Color.blurple(),
            title=s.get_text('help') )
        await EmbedPagesEmbed(ctx, embeds, timed_out_embed).send()


def setup(bot):
    load_cog(bot, General(bot))