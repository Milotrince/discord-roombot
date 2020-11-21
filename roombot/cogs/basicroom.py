import discord
from discord.ext import commands
from roombot.database.room import Room
from roombot.database.settings import Settings
from roombot.database.db import RoomBotDatabase
from roombot.utils.functions import load_cog, get_aliases, now, pop_flags
from roombot.utils.text import langs, get_text
from roombot.utils.roomembed import RoomEmbed
from roombot.utils.constants import ACCEPT_EMOJI, DECLINE_EMOJI, JOIN_EMOJI, STOP_EMOJI, LANGUAGE_EMOJI, ID_EMOJI
from random import choice

class BasicRoom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.blurple()
        self.invites = RoomBotDatabase().invites

    @commands.command()
    @commands.guild_only()
    async def new(self, ctx, *args):
        (flags, flag_args) = pop_flags(args)
        if len(flags) > 0:
            opts = {}
            keys = ['activity', 'color', 'description', 'lock', 'size', 'timeout']
            for (i, flag) in enumerate(flags):
                for key in keys:
                    if flag == key or flag in get_aliases(key):
                        opts[key] = flag_args[i]
            await Room.create(ctx.message.author, ctx=ctx, **opts)
        else:
            await Room.create(ctx.message.author, ctx=ctx, activity=' '.join(args))

    @commands.command()
    @commands.guild_only()
    async def join(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        if len(args) < 1:
            return await ctx.send(settings.get_text('missing_target_room'))
        room = Room.get_by_any(ctx, args)
        if room:
            joined = await self.try_join(ctx, room, ctx.author)
            if joined:
                await RoomEmbed(ctx, room, 'room_joined', settings).send()
            else:
                await channel.send(settings.get_text('retry_error'))
        else:
            await ctx.send(settings.get_text('room_not_exist'))


    @commands.command()
    @commands.guild_only()
    async def invite(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        if len(args) < 1:
            return await ctx.send(settings.get_text('missing_target'))
        user_mentions = ctx.message.mentions
        role_mentions = ctx.message.role_mentions
        player = ctx.message.author
        invitees = []
        room = None
        
        for invitee in user_mentions:
            if invitee.id not in invitees:
                invitees.append(invitee.id)

        for role in role_mentions:
            for member in role.members:
                if member.id not in invitees:
                    invitees.append(member.id)

        player_names = []
        for member in ctx.guild.members:
            player_names.append(member.display_name.lower())
            player_names.append(member.name.lower())

        for arg in args:
            p = discord.utils.find(lambda p: p.name.lower() == arg.lower() or p.display_name.lower() == arg.lower(), ctx.guild.members)
            if p and p.id not in invitees:
                invitees.append(p.id)

        (room, message) = Room.get_room(ctx, args)
        if not room:
            return await ctx.send(message)

        if not invitees:
            return await ctx.send(settings.get_text('missing_target_invitees'))
                    
        room.update_active()
        embed = discord.Embed(
            color=discord.Color.blurple(),
            timestamp=now(),
            title=choice(settings.get_text('invite_messages')).format(player.display_name, room.activity) )
        embed.add_field(
            inline=False,
            name=room.activity,
            value=room.description )
        embed.add_field(
            inline=False,
            name="{} ({}/{})".format(settings.get_text('players'), len(room.players), room.size),
            value="<@{}>".format(">, <@".join([str(id) for id in room.players])) )
        embed.add_field(
            inline=False,
            name=settings.get_text('inviter') + ": " + player.display_name,
            value=settings.get_text('server') + ": " + ctx.guild.name )
        embed.add_field(
            inline=True,
            name=ID_EMOJI,
            value=room.role_id )
        embed.add_field(
            inline=True,
            name=LANGUAGE_EMOJI,
            value=settings.language)
        embed.set_footer(
            text=settings.get_text('invite_instructions'),
            icon_url=discord.Embed.Empty )


        result_embed = discord.Embed(
            color=discord.Color.blurple(),
            description="{}: `{}`".format(settings.get_text('room'), room.activity),
            timestamp=now(),
            title=settings.get_text('invites_sent') )
        result_embed.set_footer(
            text="{}: {}".format(settings.get_text('inviter'), player.display_name),
            icon_url=discord.Embed.Empty )
        invitee_success = []
        invitee_fail = []
        invitee_already_joined = []
        for invitee_id in invitees:
            try:
                if invitee_id in room.players:
                    invitee_already_joined.append(invitee_id)
                    continue
                invitee = self.bot.get_user(invitee_id)
                m = await invitee.send(embed=embed)
                await m.add_reaction(ACCEPT_EMOJI)
                await m.add_reaction(DECLINE_EMOJI)
                self.invites.insert(dict(user=invitee_id, room=room.role_id))
                invitee_success.append(invitee_id)
            except discord.errors.Forbidden as e:
                invitee_fail.append(invitee_id)

        if invitee_success:
            result_embed.add_field(
                name=settings.get_text('invitees'),
                value="<@{}>".format(">, <@".join([str(id) for id in invitee_success])) )
        if invitee_fail:
            result_embed.add_field(
                name=settings.get_text('failed_invites'),
                value="{}\n<@{}>".format(settings.get_text('failed_invites_description'), ">, <@".join([str(id) for id in invitee_fail])) )
        if invitee_already_joined:
            result_embed.add_field(
                name=settings.get_text('already_joined'),
                value="<@{}>".format(">, <@".join([str(id) for id in invitee_already_joined])) )
            
        return await ctx.send(embed=result_embed)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if str(reaction) == JOIN_EMOJI and reaction.message.author.id == self.bot.user.id and not user.bot:
            room = Room.from_message(reaction.message)
            if room:
                await self.try_leave(reaction.message.channel, room, user)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.message.author.id == self.bot.user.id and not user.bot:
            if hasattr(user, 'guild'):
                if str(reaction) == JOIN_EMOJI:
                    room = Room.from_message(reaction.message)
                    if room:
                        await self.try_join(reaction.message.channel, room, user)
            else:
                await self.try_invite_response(reaction, user)

    @commands.command()
    @commands.guild_only()
    async def leave(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        rooms = Room.get_player_rooms(player.id, ctx.guild.id)
        
        room = None
        if len(rooms) > 1:
            role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions and ctx.message.role_mentions[0] else None
            text_filter = ' '.join(args).lower() if args else None
            for r in rooms:
                match_channel = ctx.channel.id == r.channel_id if ctx.channel else False
                match_text = text_filter and text_filter in r.activity.lower()
                match_role = role_mention_filter == r.role_id
                if match_channel or match_text or match_role:
                    room = r
                    break
            if not room:
                return await ctx.send(settings.get_text('in_multiple_rooms'))
        elif len(rooms) == 1:
            room = rooms[0]
        else:
            return await ctx.send(settings.get_text('not_in_room'))

        if room:
            (success, response) = await self.try_leave(ctx, room, player)
            if success and response and ctx.channel and ctx.channel.id != room.channel_id:
                try:
                    await ctx.send(response)
                except:
                    pass
        else:
            return await ctx.send(settings.get_text('no_room'))


    @commands.command()
    @commands.guild_only()
    async def ls(self, ctx):
        settings = Settings.get_for(ctx.guild.id)
        rooms = Room.find(guild=ctx.guild.id)
        embed = discord.Embed(color=discord.Color.blurple())
        count = 0

        for room_data in rooms:
            count += 1
            room = Room.from_query(room_data)

            description = room.description if room.description else "{}: {}".format(settings.get_text('players'), ', '.join(room.players))
            embed.add_field(
                name="{}{} ({}/{})".format(room.get_symbols(), room.activity, len(room.players), room.size),
                value=description,
                inline=False )
        if count > 0:
            embed.title = "{} ({})".format(settings.get_text('rooms'), count)
            await ctx.send(embed=embed)
        else:
            await ctx.send(settings.get_text('no_rooms'))


    @commands.command()
    @commands.guild_only()
    async def look(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        room = Room.get_by_any(ctx, args)
        if room:
            await RoomEmbed(ctx, room, 'request', settings).send()
        else:
            await ctx.send(settings.get_text('no_room'))


    async def try_join(self, ctx, room, player):
        settings = Settings.get_for(ctx.guild.id)
        room.update_active()
        if not settings.allow_multiple_rooms and Room.player_is_in_any(player.id, ctx.guild.id):
            return (False, settings.get_text('already_in_room'))
        if room.lock:
            return (False, settings.get_text('join_locked_room'))
        if room.size <= len(room.players):
            return (False, settings.get_text('join_full_room'))

        if await room.add_player(player):
            room_channel = ctx.guild.get_channel(room.channel_id)
            await room_channel.send(choice(settings.join_messages).format(player.display_name))
            if len(room.players) >= room.size:
                role = ctx.guild.get_role(room.role_id)
                if role:
                    await ctx.send(settings.get_text('full_room_notification').format(role.mention, len(room.players)))
            return True
        return False

    async def try_leave(self, ctx, room, player):
        settings = Settings.get_for(ctx.guild.id)
        room.update_active()
        if room.host == player.id:
            role = ctx.guild.get_role(room.role_id)
            await room.disband(ctx.guild)
            return (True, settings.get_text('disband_room').format(player.display_name, room.activity))
        elif player.id in room.players:
            (success, response) = await room.remove_player(player)
            if success:
                try:
                    room_channel = ctx.guild.get_channel(room.channel_id)
                    await room_channel.send(choice(settings.leave_messages).format(player.display_name))
                    if response:
                        await ctx.send(response)
                except:
                    pass
                return (True, settings.get_text('left_room').format(player.name, room.activity))
            else:
                return (True, settings.get_text('retry_error'))
        return (False, None)

    async def try_invite_response(self, reaction, user):
        channel = reaction.message.channel
        accept = str(reaction.emoji) == ACCEPT_EMOJI
        decline = str(reaction.emoji) == DECLINE_EMOJI
        valid_invite_emoji = accept or decline
        from_dm = type(channel) is discord.channel.DMChannel
        room_id = None
        lang = langs[0]
        for field in reaction.message.embeds[0].fields:
            if field.name == ID_EMOJI:
                room_id = field.value
            elif field.name == LANGUAGE_EMOJI:
                lang = field.value
        search = self.invites.find_one(user=user.id, room=room_id)

        if not valid_invite_emoji or not search or not from_dm:
            return

        room = None
        room_data = Room.find_one(role_id=room_id)
        if room_data:
            room = Room.from_query(room_data)
        if not room:
            return await channel.send(get_text('room_not_exist', lang=lang))

        self.invites.delete(user=user.id, room=room_id)
        settings = Settings.get_for(room.guild)

        if (accept):
            room_channel = self.bot.get_channel(room.channel_id)
            guild = self.bot.get_guild(room.guild)
            member = guild.get_member(user.id)
            if not room_channel or not guild or not member:
                return await channel.send(get_text('room_not_exist', lang=lang))
            await channel.send(get_text('invite_accepted', lang=lang))
            room.lock = False
            joined = await self.try_join(room_channel, room, member)
            if joined:
                await RoomEmbed(reaction.message, room, 'room_joined', settings).send()
            else:
                await channel.send(settings.get_text('retry_error'))
        else:
            await channel.send(get_text('invite_declined', lang=lang))


def setup(bot):
    load_cog(bot, BasicRoom(bot))