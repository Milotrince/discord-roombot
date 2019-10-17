from utility import * 
from discord.ext import commands
import discord
import os
import json
from os.path import dirname

with open(os.path.join(dirname(dirname(__file__)), 'settings.json')) as settings_file:  
    default_settings = json.load(settings_file)

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

    @commands.command(aliases=['clear', 'delete'])
    async def purge(self, ctx, *args):
        """Delete room(s) in this server (`-a` for all active rooms, `-b` for all broken rooms). For moderation purposes."""
        player = ctx.message.author
        if not player.guild_permissions.administrator:
            return await ctx.send("You are not an administrator.")

        (flags, words) = pop_flags(args)
        if 'a' not in flags and 'b' not in flags:
            return await ctx.send("Please specify a room (by `@role` or `#channel`) or a flag (`-a`, `-b`).")

        if 'b' in flags:
            deleted_channels = 0
            deleted_roles = 0
            category = discord.utils.get(player.guild.categories, name='Rooms')
            for channel in category.channels:
                if iter_len(rooms.find(guild=ctx.guild.id, channel_id=channel.id)) < 1:
                    await channel.delete()
                    deleted_channels += 1
            for role in ctx.guild.roles:
                if iter_len(rooms.find(guild=ctx.guild.id, role_id=role.id)) < 1 and role.name.startswith("Room -"):
                    await role.delete()
                    deleted_roles += 1
            try:
                await ctx.send("{} broken channels and {} broken roles have been deleted.".format(deleted_channels, deleted_roles))
            except discord.errors.NotFound as e:
                log(e)

        if 'a' in flags:
            rooms_data = rooms.find(guild=ctx.guild.id)
            if iter_len(rooms_data) < 1:
                await ctx.send("There are no rooms to delete.")
                if 'a' not in flags:
                    await ctx.send("(To delete broken rooms, use `-b`.)")
                return
            count = 0
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                guild = bot.get_guild(r.guild)
                await r.disband(guild)
                count += 1
            try:
                await ctx.send("{} rooms have been deleted.".format(count))
            except discord.errors.NotFound as e:
                log(e)