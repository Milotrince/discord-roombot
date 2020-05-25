from database.room import *
from discord.ext import commands
import discord

class Admin(commands.Cog, name=get_text('_cog')['admin']):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.red()

    async def cog_check(self, ctx):
        return ctx.message.author.guild_permissions.administrator

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            await ctx.send(get_text('not_admin'))


    @commands.command()
    async def settings(self, ctx, *args):
        """
        Set options for this server.
        To set an option(s), use `-flag value`
        """
        settings_info = {}
        for setting in Settings.defaults.keys():
            text = get_text('_commands')[setting]
            settings_info[setting] = {
                'name': text['_name'],
                'flags': text['_aliases'],
                'description': text['_help']
            }

        (flags, flag_args) = pop_flags(args)
        settings = Settings.get_for(ctx.guild.id)
        if flags:
            for i, flag in enumerate(flags):
                for field_name, field in settings_info.items():
                    if flag in field['flags'] + [field['name']]:
                        (success, message) = settings.set(ctx, field_name, flag_args[i])
                        await ctx.send(message)
        else:
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=get_text('settings'))
            for field_name, field in settings_info.items():
                field_value = settings.get(field_name)
                if isinstance(field_value, bool): 
                    field_value = bool_to_text(field_value)
                embed.add_field(
                    name="***{}***  **{}**".format(field['name'], field_value),
                    value="**{}:** `-{}`\n{}".format(get_text('flags'), "`, `-".join(field['flags']), '\n'.join(field['description']) ))
            await ctx.send(get_text('settings_instructions').format('r.'), embed=embed)


    @commands.command()
    async def force_disband(self, ctx, *args):
        rooms = rooms_db.find(guild=ctx.guild.id)
        activity_filter = " ".join(args) if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = rooms_db.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if r.activity == activity_filter or r.role_id == role_mention_filter:
                    await r.disband(ctx.guild)
                    try:
                        await ctx.send(get_text('disband_room').format('<@'+str(r.host)+'>', r.activity))
                    except discord.errors.NotFound as e:
                        pass
                        # log(e)
                    return
        return await ctx.send(get_text('room_not_exist'))


    @commands.command()
    async def purge(self, ctx, *args):
        """Delete room(s) in this server (`-a` for all active rooms_db, `-b` for all broken rooms_db). For moderation purposes."""
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        if not player.guild_permissions.administrator:
            return await ctx.send(get_text('not_admin'))

        (flags, words) = pop_flags(args)
        if 'a' not in flags and 'b' not in flags:
            return await ctx.send(get_text('purge_missing_flag'))

        if 'a' in flags or 'active' in flags:
            rooms_db_data = rooms_db.find(guild=ctx.guild.id)
            count = 0
            for room_data in rooms_db_data:
                r = Room.from_query(room_data)
                guild = self.bot.get_guild(r.guild)
                await r.disband(guild)
                count += 1
            await ctx.send(get_text('purged_a').format(count))

        if 'b' in flags or 'broken' in flags:
            deleted_channels = 0
            deleted_roles = 0
            failed_channels = 0
            failed_roles = 0
            category = discord.utils.get(player.guild.categories, name=settings.category_name)
            if not category:
                return await ctx.send(get_text('no_category'))
            for channel in category.channels:
                if iter_len(rooms_db.find(guild=ctx.guild.id, channel_id=channel.id)) < 1:
                    try:
                        await channel.delete()
                        deleted_channels += 1
                    except:
                        failed_channels += 1
            for role in ctx.guild.roles:
                if iter_len(rooms_db.find(guild=ctx.guild.id, role_id=role.id)) < 1 and role.name.startswith("(Room) "):
                    try:
                        await role.delete()
                        deleted_roles += 1
                    except:
                        failed_roles += 1

            await ctx.send(get_text('purged_b').format(deleted_channels, deleted_roles))
            if failed_channels > 0 or failed_roles > 0:
                await ctx.send(get_text('purged_b_fail').format(failed_channels, failed_roles))


def setup(bot):
    load_cog(bot, Admin(bot))