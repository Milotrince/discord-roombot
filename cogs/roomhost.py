from database.room import *
from discord.ext import commands
import discord

class RoomHost(commands.Cog, name=get_text('_cog')['host']):
    def __init__(self):
        self._last_member = None
        self.color = discord.Color.blurple()
        self.p_keys = ['player', 'room', 'room_channel', 'room_role', 'flags', 'words', 'new_value', 'mentioned_player']
        self.p = dict.fromkeys(self.p_keys)

    def get_target_player(self, ctx, args):
        name_filter = " ".join(args).lower()
        target_player = self.p['mentioned_player']
        if not target_player:
            for p in ctx.guild.members:
                if p.display_name.lower() == name_filter or p.name.lower() == name_filter:
                    target_player = p
        return target_player

    async def cog_before_invoke(self, ctx, *args):
        self.p['player'] = ctx.message.author

        is_admin = ctx.message.author.guild_permissions.administrator
        mentions = len(ctx.message.mentions)
        role_mentions = ctx.message.role_mentions

        if is_admin and (len(role_mentions) >= 1):
            self.p['room'] = Room.get_by_role(role_mentions[0].id)
        else:
            self.p['room'] = Room.get_hosted(self.p['player'].id, ctx.guild.id)

        if self.p['room']:
            self.p['mentioned_player'] = ctx.message.mentions[0] if ctx.message.mentions else None
            self.p['channel'] = ctx.guild.get_channel(self.p['room'].channel_id)
            self.p['voice_channel'] = ctx.guild.get_channel(self.p['room'].voice_channel_id)
            self.p['role'] = ctx.guild.get_role(self.p['room'].role_id)


    async def cog_after_invoke(self, ctx):
        self.p = dict.fromkeys(self.p_keys)

    async def cog_check(self, ctx):
        is_host = Room.get_hosted(ctx.message.author.id, ctx.guild.id)
        is_admin = ctx.message.author.guild_permissions.administrator
        searched_room = Room.get_by_mention(ctx, ctx.message.content.split(' ')[1:])
        return is_host or is_admin and searched_room

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            await ctx.send(get_text('not_host'))


    @commands.command()
    async def kick(self, ctx, *args):
        """
        Kick a player.
        Can either mention or use the name of the kickee.
        """
        kickee = self.get_target_player(ctx, args)
        if not kickee:
            return await ctx.send(get_text('missing_target'))
        if self.p['player'].id == kickee.id:
            return await ctx.send(get_text('self_target').format(self.p['player'].display_name))
        if kickee.id in self.p['room'].players:
            await self.p['room'].remove_player(kickee)
            await ctx.send(get_text('kicked').format(self.p['player'].display_name, kickee.display_name, self.p['room'].activity))
            if len(self.p['room'].players) < 1:
                await self.p['room'].disband(self.p['player'].guild)
                return await ctx.send(get_text('disband_empty_room'))
        else:
            return await ctx.send(get_text('target_not_in_room').format(kickee.display_name, self.p['channel'].mention))


    @commands.command()
    async def host(self, ctx, *args):
        """
        Change the host of your room.
        Can either mention or use the name of new host.
        """
        new_host = self.get_target_player(ctx, args)
        if not new_host:
            return await ctx.send(get_text('missing_target'))
        for p in self.p['room'].players:
            if p == new_host.id:
                self.p['room'].host = new_host.id
                self.p['room'].update('host', new_host.id)
                return await ctx.send(get_text('new_host').format(self.p['player'].display_name, new_host.mention, self.p['channel'].mention))
        return await ctx.send(get_text('target_not_in_room').format(new_host.display_name, self.p['channel'].mention))


    @commands.command()
    async def edit(self, ctx, *args):
        """
        Edit room information using flags.
        For example, `r.edit -activity myNewGame -size 4`.
        You can use aliases (ex. `-a` for `-activity`).
        """
        fields = {
            'activity': self.activity.aliases,
            'description': self.description.aliases,
            'size': self.size.aliases,
            'host': self.host.aliases,
            'colour': self.colour.aliases }
        (flags, flag_args) = pop_flags(args)

        if len(flags) < 2:
            return await ctx.send(get_text('require_flags'))

        for i, flag in enumerate(flags):
            valid = False
            for field, aliases in fields.items():
                if flag == field or flag in aliases:
                    if field == 'activity':
                        await self.activity.callback(self, ctx, *tuple(flag_args))
                    elif field == 'description':
                        await self.description.callback(self, ctx, *tuple(flag_args))
                    elif field == 'size':
                        await self.size.callback(self, ctx, *tuple(flag_args))
                    elif field == 'host':
                        await self.host.callback(self, ctx, *tuple(flag_args))
                    elif field == 'colour':
                        await self.colour.callback(self, ctx, *tuple(flag_args))
                    elif field == 'timeout':
                        await self.timeout.callback(self, ctx, *tuple(flag_args))
                    valid = True
                    break
            if not valid:
                await ctx.send(get_text('bad_field').format(flag))


    @commands.command()
    async def activity(self, ctx, *args):
        """
        Set the name of your room.
        This is what the channel and role will be named as.
        """
        new_activity = remove_mentions(' '.join(args))
        if len(new_activity) < 1:
            new_activity = choice(get_text('default_room_names')).format(ctx.message.author.display_name)
        await self.p['role'].edit(name="(Room) " + new_activity)
        await self.p['channel'].edit(name=new_activity)
        if self.p['voice_channel']:
            await self.p['voice_channel'].edit(name=new_activity)
        self.p['room'].activity = new_activity
        self.p['room'].update('activity', new_activity)
        return await ctx.send(get_text('updated_field').format(get_text('activity'), new_activity, self.p['player'].display_name, self.p['channel'].mention))


    @commands.command()
    async def description(self, ctx, *args):
        """
        Set the description of your room.
        The description is the little message that you will see in the room list.
        """
        new_description = remove_mentions(' '.join(args))
        self.p['room'].description = new_description
        self.p['room'].update('description', new_description)
        await self.p['channel'].edit(topic="({}/{}) {}".format(len(self.p['room'].players), self.p['room'].size, self.p['room'].description))
        return await ctx.send(get_text('updated_field').format(get_text('description'), new_description, self.p['player'].display_name, self.p['channel'].mention))


    @commands.command()
    async def size(self, ctx, *args):
        """
        Set the max player size of your room.
        Once the room is full, I will ping the room.
        """
        try:
            new_size = clamp(int(remove_mentions(args)[0]), 2, 999) if remove_mentions(args) else None
            if len(self.p['room'].players) > new_size:
                return await ctx.send(get_text('size_too_small'))
            self.p['room'].size = new_size
            self.p['room'].update('size', new_size)
            return await ctx.send(get_text('updated_field').format(get_text('size'), new_size, self.p['player'].display_name, self.p['channel'].mention))
        except ValueError:
            return await ctx.send(get_text('need_integer'))


    @commands.command()
    async def timeout(self, ctx, *args):
        new_timeout = remove_mentions(args)[0] if remove_mentions(args) else False 
        try:
            new_timeout = min(int(new_timeout), 999)
            if (new_timeout < 0):
                raise ValueError
        except ValueError:
            new_timeout = -1
        self.p['room'].timeout = new_timeout
        self.p['room'].update('timeout', new_timeout)
        return await ctx.send(get_text('updated_field').format(get_text('timeout'), new_timeout, self.p['player'].display_name, self.p['channel'].mention))


    @commands.command()
    async def lock(self, ctx, *args):
        first_arg = remove_mentions(args)[0]
        new_lock = text_to_bool(first_arg) if len(first_arg) > 0 else not self.p['room'].lock 
        self.p['room'].update('lock', new_lock)
        return await ctx.send(get_text('lock_room') if new_lock else get_text('unlock_room'))


    # @commands.command()
    # async def public(self, ctx, *args):
    #     new_public = text_to_bool(remove_mentions(args)[0]) if remove_mentions(args) else not self.p['room'].public
    #     self.p['room'].update('public', new_public)
    #     if new_public:
    #         self.p['channel'].edit(overwrites={})
    #     return await ctx.send(get_text('updated_field').format(get_text('public'), new_public, self.p['player'].display_name, self.p['channel'].mention))


    @commands.command()
    async def color(self, ctx, *args):
        """
        Set the color of your room.
        Possible colors are: teal, green, blue, purple, magenta/pink,
        gold/yellow, orange, and red.
        A random color is set if the specified color is not included above.
        """
        c = get_color(remove_mentions(args)[0] if remove_mentions(args) else '') 
        await self.p['role'].edit(color=c)
        self.p['room'].update('color', c.value)
        return await ctx.send(get_text('updated_field').format(get_text('color'), c, self.p['player'].display_name, self.p['channel'].mention))


    @commands.command()
    async def voice_channel(self, ctx, *args):
        """
        Create a voice channel associated with this room.
        Will not create if already exists.
        """
        if self.p['voice_channel']:
            return await ctx.send(get_text('voice_channel_exists'))
        category = await get_rooms_category(ctx.guild)
        settings = Settings.get_for(ctx.guild.id)
        voice_channel = await ctx.guild.create_voice_channel(
            self.p['room'].activity,
            category=category,
            position=0,
            bitrate=settings.bitrate * 1000, 
            overwrites={
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(move_members=True),
                self.p['role']: discord.PermissionOverwrite(read_messages=True) })
        self.p['room'].update('voice_channel_id', voice_channel.id)
        return await ctx.send(get_text('new_voice_channel').format(voice_channel.name))


def setup(bot):
    load_cog(bot, RoomHost())