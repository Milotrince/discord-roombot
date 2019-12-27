from room import *
from discord.ext import commands
import discord

class Admin(commands.Cog, name=strings['_cog']['admin']):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.red()

    async def cog_check(self, ctx):
        return ctx.message.author.guild_permissions.administrator

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            await ctx.send(strings['not_admin'])

    @commands.command()
    async def settings(self, ctx, *args):
        """
        Set options for this server.
        To set an option(s), use `-flag value`
        """
        (flags, flag_args) = pop_flags(args)
        settings = Settings.get_for(ctx.guild.id)
        if flags:
            for i, flag in enumerate(flags):
                for field_name, field in Settings.format.items():
                    if flag in field['flags']:
                        (success, message) = settings.set(field_name, flag_args[i])
                        await ctx.send(message)
        else:
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=strings['settings'])
            for field_name, field in Settings.format.items():
                field_value = settings.get(field_name)
                if isinstance(field_value, bool): 
                    field_value = bool_to_text(field_value)
                embed.add_field(
                    name="***{}***  **{}**".format(field_name, field_value),
                    value="**{}:** `-{}`\n{}".format(strings['flags'], "`, `-".join(field['flags']), field['description'] ))
            await ctx.send(strings['settings_instructions'].format('r.'), embed=embed)
            

    @commands.command()
    async def purge(self, ctx, *args):
        """Delete room(s) in this server (`-a` for all active rooms_db, `-b` for all broken rooms_db). For moderation purposes."""
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        if not player.guild_permissions.administrator:
            return await ctx.send(strings['not_admin'])

        (flags, words) = pop_flags(args)
        if 'a' not in flags and 'b' not in flags:
            return await ctx.send(strings['purge_missing_flag'])

        if 'b' in flags:
            deleted_channels = 0
            deleted_roles = 0
            category = discord.utils.get(player.guild.categories, name=settings.category_name)
            if not category:
                return await ctx.send(strings['no_category'])
            for channel in category.channels:
                if iter_len(rooms_db.find(guild=ctx.guild.id, channel_id=channel.id)) < 1:
                    await channel.delete()
                    deleted_channels += 1
            for role in ctx.guild.roles:
                if iter_len(rooms_db.find(guild=ctx.guild.id, role_id=role.id)) < 1 and role.name.startswith("(Room) "):
                    await role.delete()
                    deleted_roles += 1
            try:
                await ctx.send(strings['purged_b'].format(deleted_channels, deleted_roles))
            except discord.errors.NotFound as e:
                log(e)

        if 'a' in flags:
            rooms_db_data = rooms_db.find(guild=ctx.guild.id)
            count = 0
            for room_data in rooms_db_data:
                r = Room.from_query(room_data)
                guild = self.bot.get_guild(r.guild)
                await r.disband(guild)
                count += 1
            try:
                await ctx.send(strings['purged_a'].format(count))
            except discord.errors.NotFound as e:
                log(e)


def setup(bot):
    bot.add_cog(Admin(bot))