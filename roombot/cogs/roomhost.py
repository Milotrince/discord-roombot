from roombot.database.room import *
from discord.ext import commands
import discord

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
        is_host = Room.get_hosted(ctx.message.author.id, ctx.guild.id)
        is_admin = ctx.message.author.guild_permissions.administrator
        searched_room = Room.get_by_mention(ctx, ctx.message.content.split(' ')[1:])
        return (is_host and is_enabled_command) or (is_admin and searched_room)

    async def cog_command_error(self, ctx, error):
        s = Settings.get_for(ctx.guild.id)
        if type(error) == discord.ext.commands.errors.CheckFailure:
            await ctx.send(s.get_text('host_command_fail'))

    def get_context(self, ctx, *args):
        is_admin = ctx.message.author.guild_permissions.administrator
        mentions = len(ctx.message.mentions)
        role_mentions = ctx.message.role_mentions
        player = ctx.message.author
        context = RoomContext(
            ctx=ctx,
            settings=Settings.get_for(ctx.guild.id),
            args=list(list(args)[0]),
            player=player )
        if is_admin and (len(role_mentions) >= 1):
            room = Room.get_by_role(role_mentions[0].id)
        else:
            room = Room.get_hosted(player.id, ctx.guild.id)
        if room:
            context.room = room
            context.mentioned_player = ctx.message.mentions[0] if ctx.message.mentions else None
            context.channel = ctx.guild.get_channel(room.channel_id)
            context.voice_channel = ctx.guild.get_channel(room.voice_channel_id)
            context.role = ctx.guild.get_role(room.role_id)
        return context

    def get_target_player(self, c):
        name_filter = " ".join(c.args).lower()
        target_player = c.mentioned_player
        if not target_player:
            for p in c.ctx.guild.members:
                if p.display_name.lower() == name_filter or p.name.lower() == name_filter:
                    target_player = p
        return target_player
    

    @commands.command()
    @commands.guild_only()
    async def kick(self, ctx, *args):
        c = self.get_context(ctx, args)
        kickee = self.get_target_player(c)
        if not kickee:
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
            return await ctx.send(c.settings.get_text('target_not_in_room').format(kickee.display_name, c.channel.mention))


    @commands.command()
    @commands.guild_only()
    async def host(self, ctx, *args):
        c = self.get_context(ctx, args)
        new_host = self.get_target_player(c)
        if not new_host:
            return await ctx.send(c.settings.get_text('missing_target'))
        for p in c.room.players:
            if p == new_host.id:
                c.room.host = new_host.id
                c.room.update('host', new_host.id)
                c.room.host = new_host.id
                return await ctx.send(c.settings.get_text('new_host').format(c.player.display_name, new_host.mention, c.channel.mention))
        return await ctx.send(c.settings.get_text('target_not_in_room').format(new_host.display_name, c.channel.mention))


    @commands.command()
    @commands.guild_only()
    async def activity(self, ctx, *args):
        c = self.get_context(ctx, args)
        new_activity = remove_mentions(' '.join(args))
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
        return await ctx.send(c.settings.get_text('updated_field').format(c.settings.get_text('activity'), new_activity, player_name, c.channel.mention))


    @commands.command()
    @commands.guild_only()
    async def description(self, ctx, *args):
        c = self.get_context(ctx, args)
        new_description = remove_mentions(' '.join(args))
        topic = "({}/{}) {}".format(len(c.room.players), c.room.size, c.room.description)
        try:
            await asyncio.wait_for(c.channel.edit(topic=topic), timeout=3.0)
        except asyncio.TimeoutError:
            return await ctx.send(c.settings.get_text('rate_limited'))
        c.room.description = new_description
        c.room.update('description', new_description)
        return await ctx.send(c.settings.get_text('updated_field').format(c.settings.get_text('description'), new_description, c.player.display_name, c.channel.mention))


    @commands.command()
    @commands.guild_only()
    async def size(self, ctx, *args):
        c = self.get_context(ctx, args)
        try:
            new_size = clamp(int(remove_mentions(args)[0]), 2, 999) if remove_mentions(args) else None
            if len(c.room.players) > new_size:
                return await ctx.send(c.settings.get_text('size_too_small'))
            c.room.size = new_size
            c.room.update('size', new_size)
            return await ctx.send(c.settings.get_text('updated_field').format(c.settings.get_text('size'), new_size, c.player.display_name, c.channel.mention))
        except ValueError:
            return await ctx.send(c.settings.get_text('need_integer'))


    @commands.command()
    @commands.guild_only()
    async def timeout(self, ctx, *args):
        c = self.get_context(ctx, args)
        new_timeout = remove_mentions(args)[0] if remove_mentions(args) else False 
        try:
            new_timeout = min(int(new_timeout), 999)
            if (new_timeout < 0):
                raise ValueError
        except ValueError:
            new_timeout = -1
        c.room.timeout = new_timeout
        c.room.update('timeout', new_timeout)
        return await ctx.send(c.settings.get_text('updated_field').format(c.settings.get_text('timeout'), new_timeout, c.player.display_name, c.channel.mention))


    @commands.command()
    @commands.guild_only()
    async def lock(self, ctx, *args):
        c = self.get_context(ctx, args)
        first_arg = remove_mentions(args)[0]
        new_lock = text_to_bool(first_arg) if len(first_arg) > 0 else not c.room.lock 
        c.room.update('lock', new_lock)
        return await ctx.send(c.settings.get_text('lock_room') if new_lock else c.settings.get_text('unlock_room'))


    @commands.command()
    @commands.guild_only()
    async def color(self, ctx, *args):
        c = self.get_context(ctx, args)
        color = get_color(remove_mentions(args)[0] if remove_mentions(args) else '') 
        try:
            await asyncio.wait_for(c.role.edit(color=color), timeout=3.0)
        except asyncio.TimeoutError:
            return await ctx.send(c.settings.get_text('rate_limited'))
        c.room.update('color', color.value)
        return await ctx.send(c.settings.get_text('updated_field').format(c.settings.get_text('color'), color, c.player.display_name, c.channel.mention))

    # TODO: set view/send perms
    # @commands.command()
    # @commands.guild_only()
    # async def view_permission(self, ctx, *args):
    #     pass

    # @commands.command()
    # async def send_permission(self, ctx, *args):
    #     pass

    @commands.command()
    @commands.guild_only()
    async def voice_channel(self, ctx, *args):
        c = self.get_context(ctx, args)
        if c.voice_channel:
            # TODO: calling vc again destroys the vc
            return await ctx.send(c.settings.get_text('voice_channel_exists'))
        category = await get_rooms_category(ctx.guild)
        settings = Settings.get_for(ctx.guild.id)
        voice_channel = await ctx.guild.create_voice_channel(
            c.room.activity,
            category=category,
            position=0,
            bitrate=settings.bitrate * 1000, 
            overwrites={
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(move_members=True),
                c.role: discord.PermissionOverwrite(read_messages=True) })
        c.room.update('voice_channel_id', voice_channel.id)
        return await ctx.send(c.settings.get_text('new_voice_channel').format(voice_channel.name))


def setup(bot):
    load_cog(bot, RoomHost())