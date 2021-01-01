import discord
from discord.ext import commands
from roombot.database.room import Room
from roombot.database.settings import Settings
from roombot.utils.functions import load_cog, get_target, get_rooms_category, get_color, pop_flags, clean_args, text_to_bool, clamp
from roombot.utils.text import get_all_text
from random import choice
import asyncio
import re

class RoomContext(object):
    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])


class RoomHost(commands.Cog):
    def __init__(self):
        self.color = discord.Color.blurple()

    async def cog_check(self, ctx):
        s = Settings.get_for(ctx.guild.id)
        is_enabled_command = ctx.command.name in s.allowed_host_commands
        if not is_enabled_command:
            await ctx.send(s.get_text('host_command_disabled'))
            return False
        return True

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            return

    async def get_context(self, ctx, args):
        is_admin = ctx.message.author.guild_permissions.administrator
        mentions = len(ctx.message.mentions)
        role_mentions = ctx.message.role_mentions
        player = ctx.message.author
        context = RoomContext(
            ctx=ctx,
            settings=Settings.get_for(ctx.guild.id),
            args=list(args) if args else [],
            player=player )
        if is_admin and (len(role_mentions) >= 1):
            room = Room.get_by_role(role_mentions[0].id)
        else:
            (room, m) = Room.get_hosted_rooms(ctx, context.args)
            if m:
                await ctx.send(m)
                raise discord.ext.commands.errors.CheckFailure()
        if room:
            context.room = room
            context.channel = ctx.guild.get_channel(room.channel_id)
            context.voice_channel = ctx.guild.get_channel(room.voice_channel_id)
            context.role = ctx.guild.get_role(room.role_id)
        return context

    def get_target_player(self, c):
        target_player = c.ctx.message.mentions[0] if c.ctx.message.mentions else None
        if not target_player:
            target_player = get_target(c.ctx.guild, ' '.join(c.args), role=False)
        return target_player
    

    @commands.command()
    @commands.guild_only()
    async def kick(self, ctx, *args):
        c = await self.get_context(ctx, args)
        kickee = self.get_target_player(c)
        if not kickee or len(args) < 1:
            return await ctx.send(c.settings.get_text('missing_target'))
        if c.player.id == kickee.id:
            return await ctx.send(c.settings.get_text('self_target').format(c.player.display_name))
        if kickee.id in c.room.players:
            await c.room.remove_player(kickee)
            await ctx.send(c.settings.get_text('kicked').format(c.player.display_name, kickee.display_name, c.room.activity))
            if len(c.room.players) < 1:
                await c.room.disband(c.player.guild)
                return await ctx.send(c.settings.get_text('disband_empty_room'))
        else:
            return await ctx.send(c.settings.get_text('target_not_in_room').format(kickee.display_name))


    @commands.command()
    @commands.guild_only()
    async def host(self, ctx, *args):
        c = await self.get_context(ctx, args)
        new_host = self.get_target_player(c)
        if not new_host or len(args) < 1:
            return await ctx.send(c.settings.get_text('missing_target'))
        for p in c.room.players:
            if p == new_host.id:
                c.room.host = new_host.id
                c.room.update('host', new_host.id)
                overwrites = c.channel.overwrites
                overwrites[new_host] = discord.PermissionOverwrite(manage_channels=True)
                overwrites[c.player] = discord.PermissionOverwrite(manage_channels=None)
                await c.channel.edit(overwrites=overwrites)
                return await ctx.send(c.settings.get_text('new_host').format(c.player.display_name, new_host.mention, c.room.activity))
        return await ctx.send(c.settings.get_text('target_not_in_room').format(new_host.display_name, c.room.activity))


    @commands.command()
    @commands.guild_only()
    async def activity(self, ctx, *args):
        c = await self.get_context(ctx, args)
        new_activity = ' '.join(clean_args(args))
        player_name = c.player.display_name
        if len(new_activity) < 1:
            new_activity = choice(c.settings.default_names).format(player_name)
        try:
            await asyncio.wait_for(c.channel.edit(name=new_activity), timeout=3.0)
        except asyncio.TimeoutError:
            return await ctx.send(c.settings.get_text('rate_limited'))
        await c.role.edit(name="({}) {}".format(c.settings.get_text('room'), new_activity))
        if c.voice_channel:
            await c.voice_channel.edit(name=new_activity)
        c.room.activity = new_activity
        c.room.update('activity', new_activity)
        return await ctx.send(c.settings.get_text('updated_field_to').format(c.settings.get_text('activity'), new_activity, player_name, c.room.activity))


    @commands.command()
    @commands.guild_only()
    async def description(self, ctx, *args):
        c = await self.get_context(ctx, args)
        new_description = ' '.join(clean_args(args))
        topic = "({}/{}) {}".format(len(c.room.players), c.room.size, c.room.description)
        try:
            await asyncio.wait_for(c.channel.edit(topic=topic), timeout=3.0)
        except asyncio.TimeoutError:
            return await ctx.send(c.settings.get_text('rate_limited'))
        c.room.description = new_description
        c.room.update('description', new_description)
        return await ctx.send(c.settings.get_text('updated_field_to').format(c.settings.get_text('description'), new_description, c.player.display_name, c.room.activity))


    @commands.command()
    @commands.guild_only()
    async def size(self, ctx, *args):
        c = await self.get_context(ctx, args)
        try:
            new_size = clamp(int(clean_args(args)[0]), 2, 999) if clean_args(args) else None
            if len(c.room.players) > new_size:
                return await ctx.send(c.settings.get_text('size_too_small'))
            c.room.size = new_size
            c.room.update('size', new_size)
            return await ctx.send(c.settings.get_text('updated_field_to').format(c.settings.get_text('size'), new_size, c.player.display_name, c.room.activity))
        except ValueError:
            return await ctx.send(c.settings.get_text('need_integer'))


    @commands.command()
    @commands.guild_only()
    async def timeout(self, ctx, *args):
        c = await self.get_context(ctx, args)
        new_timeout = clean_args(args)[0] if clean_args(args) else False 
        try:
            new_timeout = min(int(new_timeout), 999)
            if (new_timeout < 0):
                raise ValueError
        except ValueError:
            new_timeout = -1
        c.room.timeout = new_timeout
        c.room.update('timeout', new_timeout)
        return await ctx.send(c.settings.get_text('updated_field_to').format(c.settings.get_text('timeout'), new_timeout, c.player.display_name, c.room.activity))


    @commands.command()
    @commands.guild_only()
    async def lock(self, ctx, *args):
        c = await self.get_context(ctx, args)
        first_arg = clean_args(args)[0]
        new_lock = text_to_bool(first_arg) if len(first_arg) > 0 else not c.room.lock 
        c.room.update('lock', new_lock)
        return await ctx.send(c.settings.get_text('lock_room') if new_lock else c.settings.get_text('unlock_room'))


    @commands.command()
    @commands.guild_only()
    async def nsfw(self, ctx, *args):
        c = await self.get_context(ctx, args)
        first_arg = clean_args(args)[0]
        new_nsfw = text_to_bool(first_arg) if len(first_arg) > 0 else not c.room.nsfw
        await c.channel.edit(nsfw=new_nsfw)
        c.room.update('nsfw', new_nsfw)
        return await ctx.send(c.settings.get_text('updated_field_to').format(c.settings.get_text('nsfw'), new_nsfw, c.player.display_name, c.room.activity))


    @commands.command()
    @commands.guild_only()
    async def color(self, ctx, *args):
        c = await self.get_context(ctx, args)
        color = get_color(clean_args(args)[0] if clean_args(args) else '') 
        try:
            await asyncio.wait_for(c.role.edit(color=color), timeout=3.0)
        except asyncio.TimeoutError:
            return await ctx.send(c.settings.get_text('rate_limited'))
        c.room.update('color', color.value)
        return await ctx.send(c.settings.get_text('updated_field_to').format(c.settings.get_text('color'), color, c.player.display_name, c.room.activity))


    @commands.command()
    @commands.guild_only()
    async def voice_channel(self, ctx, *args):
        c = await self.get_context(ctx, args)
        if c.voice_channel:
            await c.voice_channel.delete()
            await ctx.send(c.settings.get_text('deleted_voice_channel'))
        else:
            category = await get_rooms_category(ctx.guild, c.settings)
            voice_channel = await ctx.guild.create_voice_channel(
                c.room.activity,
                category=category,
                position=0,
                bitrate=c.settings.bitrate * 1000, 
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(move_members=True),
                    c.role: discord.PermissionOverwrite(read_messages=True) })
            c.room.update('voice_channel_id', voice_channel.id)
            await ctx.send(c.settings.get_text('new_voice_channel').format(voice_channel.name))


    @commands.command()
    @commands.guild_only()
    async def grant_permissions(self, ctx, *args):
        c = await self.get_context(ctx, args)
        await set_permissions(c, True)


    @commands.command()
    @commands.guild_only()
    async def remove_permissions(self, ctx, *args):
        c = await self.get_context(ctx, args)
        await set_permissions(c, False)
        

    @commands.command()
    @commands.guild_only()
    async def reset_permissions(self, ctx, *args):
        c = await self.get_context(ctx, args)
        category = await get_rooms_category(ctx.guild, c.settings)
        overwrites = category.overwrites
        await c.channel.edit(overwrites=overwrites)
        if c.voice_channel:
            await c.voice_channel.edit(overwrites=overwrites)
        await c.ctx.send(c.settings.get_text('updated_field').format(
            c.settings.get_text('permissions'),
            c.ctx.author.display_name,
            c.room.activity
        ))
        

async def set_permissions(c, grant):
    perms = ['read_messages', 'send_messages', 'connect', 'speak']
    (perm_args, target_args) = pop_flags(c.args)
    perm_dict = {}
    for (i, perm_arg) in enumerate(perm_args):
        for perm in perms:
            if perm_arg in get_all_text(perm):
                perm_dict[perm] = re.split('[,\s]+', target_args[i])
                break
    if not perm_dict:
        return await c.ctx.send(c.settings.get_text('require_flags'))
    overwrites = {}
    for (perm, target_args) in perm_dict.items():
        for t in target_args:
            target = get_target(c.ctx.guild, t)
            if target:
                if target in overwrites:
                    overwrites[target].update(**{perm:grant})
                else:
                    overwrites[target] = discord.PermissionOverwrite(**{perm:True})
    await c.channel.edit(overwrites=overwrites)
    if c.voice_channel:
        await c.voice_channel.edit(overwrites=overwrites)
    await c.ctx.send(c.settings.get_text('updated_field').format(
        c.settings.get_text('permissions'),
        c.ctx.author.display_name,
        c.room.activity
    ))


def setup(bot):
    load_cog(bot, RoomHost())