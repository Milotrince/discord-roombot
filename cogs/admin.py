from room import *
from discord.ext import commands
import discord

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.red()

    async def cog_check(self, ctx):
        return ctx.message.author.guild_permissions.administrator

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            await ctx.send("You are not an administrator.")

    @commands.command(aliases=['set', 'options', 'config'])
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
                title="Settings" )
            for field_name, field in Settings.format.items():
                field_value = settings.get(field_name)
                if isinstance(field_value, bool): field_value = bool_to_text(field_value)
                embed.add_field(
                    name="***{}***  **{}**".format(field_name, field_value),
                    value="**flags:** `-{}`\n{}".format("`, `-".join(field['flags']), field['description'] ))
            await ctx.send("To set an option(s), use `{}settings -flag value`".format('r.'), embed=embed)
            

    @commands.command(aliases=['clear', 'delete'])
    async def purge(self, ctx, *args):
        """Delete room(s) in this server (`-a` for all active rooms_db, `-b` for all broken rooms_db). For moderation purposes."""
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        if not player.guild_permissions.administrator:
            return await ctx.send("You are not an administrator.")

        (flags, words) = pop_flags(args)
        if 'a' not in flags and 'b' not in flags:
            return await ctx.send("Please specify a room (by `@role` or `#channel`) or a flag (`-a`, `-b`).")

        if 'b' in flags:
            deleted_channels = 0
            deleted_roles = 0
            category = discord.utils.get(player.guild.categories, name=settings.category_name)
            if not category:
                return await ctx.send("Could not find channel category.")
            for channel in category.channels:
                if iter_len(rooms_db.find(guild=ctx.guild.id, channel_id=channel.id)) < 1:
                    await channel.delete()
                    deleted_channels += 1
            for role in ctx.guild.roles:
                if iter_len(rooms_db.find(guild=ctx.guild.id, role_id=role.id)) < 1 and role.name.startswith("(Room) "):
                    await role.delete()
                    deleted_roles += 1
            try:
                await ctx.send("{} broken channels and {} broken roles have been deleted.".format(deleted_channels, deleted_roles))
            except discord.errors.NotFound as e:
                log(e)

        if 'a' in flags:
            rooms_db_data = rooms_db.find(guild=ctx.guild.id)
            if iter_len(rooms_db_data) < 1:
                await ctx.send("There are no rooms to delete.")
                if 'a' not in flags:
                    await ctx.send("(To delete broken rooms, use `-b`.)")
                return
            count = 0
            for room_data in rooms_db_data:
                r = Room.from_query(room_data)
                guild = bot.get_guild(r.guild)
                await r.disband(guild)
                count += 1
            try:
                await ctx.send("{} rooms have been deleted.".format(count))
            except discord.errors.NotFound as e:
                log(e)