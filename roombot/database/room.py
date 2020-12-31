import asyncio
import discord
import re
from roombot.database.db import RoomBotDatabase
from roombot.database.settings import Settings
from roombot.utils.roomembed import RoomEmbed
from roombot.utils.functions import get_rooms_category, get_color, now, utime, remove_mentions, try_delete, ids_to_str, str_to_ids
from roombot.utils.text import get_all_text
from random import choice

db = RoomBotDatabase()

class Room:
    props = {
        'role_id': 0,
        'channel_id': 0,
        'voice_channel_id': 0,
        'birth_channel': 0,
        'guild': 0,
        'host': 0,
        'players': [],
        'size': 1,
        'color': discord.Color.blurple(),
        'lock': False,
        'nsfw': False,
        'activity': '',
        'description': '',
        'timeout': 0,
        'created': now(),
        'last_active': now(),
    }

    def __init__(self, data={}, **kwargs):
        data.update(kwargs)
        self.unpack_data(data)
        db.rooms.upsert(self.pack_data(), ['role_id'])
    
    def unpack_data(self, data):
        for (key, value) in self.props.items():
            if key in data and data[key] != None:
                v = self.unpack_value(data[key], value)
                self.__setattr__(key, v)
            else:
                self.__setattr__(key, value)

    
    @classmethod
    def unpack_value(cls, value, default):
        v = value
        if isinstance(default, list) and isinstance(v, str):
            v = str_to_ids(v)
        elif isinstance(default, int) and not isinstance(v, int):
            try:
                v = int(v)
            except ValueError:
                v = -1
        elif isinstance(default, bool) and not isinstance(v, bool):
            v = bool(v)
        elif isinstance(default, discord.Color) and isinstance(v, discord.Color):
            v = v.value
        return v
    
    def pack_data(self):
        data = {}
        for (key, value) in self.props.items():
            s = self.__getattribute__(key)
            if s == None:
                s = value
            elif isinstance(value, list) and isinstance(s, list):
                s = ids_to_str(s)
            elif isinstance(value, int) and not isinstance(s, int):
                s = int(s)
            elif isinstance(value, discord.Color) and isinstance(s, discord.Color):
                s = s.value
            data[key] = s
        return data
       
         
    @classmethod
    async def create(cls, member, ctx=None, **flags):
        player = member
        guild = member.guild
        settings = Settings.get_for(guild.id)

        def flag(key):
            return cls.unpack_value(flags[key], cls.props[key]) if key in settings.allowed_host_commands and key in flags and len(flags[key]) > 0 else None

        if not guild.me.guild_permissions.manage_channels or not guild.me.guild_permissions.manage_roles:
            raise discord.ext.commands.errors.CommandInvokeError("Missing Permissons")

        # check if able to make room
        if not settings.allow_multiple_rooms and cls.player_is_in_any(player.id, guild.id):
            if ctx:
                await ctx.send(settings.get_text('already_in_room'))
            return

        # activity (room name)
        name = player.display_name
        top = player.top_role.name
        bottom = player.roles[1].name if len(player.roles) > 1 else top
        activity = flag('activity') or choice(settings.default_names).format(name, top, bottom)
        activity = activity[0:90].strip()

        # color
        if flag('color'):
            color = get_color(flag('color'))
        elif settings.use_role_color and player.top_role.color != discord.Color.default():
            color = player.top_role.color
        else:
            color = discord.Color(int(choice(settings.default_colors)))

        # role
        role = await guild.create_role(
            name="({}) {}".format(settings.get_text('room'), activity),
            color=color,
            hoist=True,
            mentionable=True )

        # overwrites
        accessors_ids = settings.access_all_rooms_role
        accessors = []
        for accessor_id in accessors_ids:
            accessor_player = guild.get_member(accessor_id)
            accessor_role = guild.get_role(accessor_id)
            if accessor_player:
                accessors.append(accessor_player)
            elif accessor_role:
                accessors.append(accessor_role)
        if len(accessors) < 1:
            accessors = list(filter(lambda m : m.bot, guild.members))

        overwrites = {
            guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True),
            role: discord.PermissionOverwrite(read_messages=True),
            player: discord.PermissionOverwrite(manage_channels=True)
        }
        for accessor in accessors:
            overwrites[accessor] = discord.PermissionOverwrite(read_messages=True)

        # channel
        category = await get_rooms_category(guild, settings)
        o = category.overwrites
        o.update(overwrites)
        overwrites = o
        channel = await category.create_text_channel(
            name=activity,
            position=0,
            overwrites=overwrites
        )

        voice_channel = None
        if settings.default_voice_channel:
            voice_channel = await guild.create_voice_channel(
                name=activity,
                bitrate=settings.bitrate * 1000,
                category=category,
                position=0,
                overwrites=overwrites
            )

        # new room
        room = Room(
            role_id=role.id,
            channel_id=channel.id,
            voice_channel_id=voice_channel.id if voice_channel else 0,
            guild=guild.id,
            birth_channel=ctx.message.channel.id if ctx else 0,
            host=player.id,
            players=[player.id],
            activity=activity,
            color=color,
            lock=flag('lock') or settings.default_lock,
            nsfw=flag('nsfw') or settings.default_nsfw,
            description=flag('description') or choice(settings.default_descriptions),
            size=flag('size') or settings.default_size,
            timeout=flag('timeout') or settings.default_timeout,
            created=now(),
            last_active=now()
        )
        await player.add_roles(role)
        await channel.edit(
            topic="({}/{}) {}".format(len(room.players), room.size, room.description),
            nsfw=room.nsfw )
        await channel.send(choice(settings.join_messages).format(player.display_name))
        if ctx:
            await RoomEmbed(ctx, room, 'new_room', settings).send()


            
    @classmethod
    def from_query(cls, data):
        return cls(data)

    @classmethod
    def from_message(cls, message):
        for field in message.embeds[0].fields:
            if field.name in get_all_text('channel'):
                channel_id = field.value[2:-1] # removes mention
                room_data = cls.find_one(channel_id=channel_id)
                if room_data:
                    return cls.from_query(room_data)


    @classmethod
    def get_room(cls, ctx, args):
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        rooms = Room.get_player_rooms(player.id, ctx.guild.id)
        
        room = None
        if len(rooms) > 1:
            role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions and ctx.message.role_mentions[0] else None
            string = ' '.join(args).lower()
            rx = re.search(r'\((.*?)\)', string)
            text_filter = rx.group(1) if rx else remove_mentions(string)
            for r in rooms:
                match_channel = ctx.channel.id == r.channel_id if ctx.channel else False
                match_text = text_filter and text_filter in r.activity.lower()
                match_role = role_mention_filter == r.role_id
                if match_channel or match_text or match_role:
                    room = r
                    break
            if not room:
                return (None, settings.get_text('in_multiple_rooms'))
        elif len(rooms) == 1:
            room = rooms[0]
        else:
            return (None, settings.get_text('not_in_room'))

        return (room, None)

    @classmethod
    def get_hosted_rooms(cls, ctx, args):
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        rooms = Room.get_player_rooms(player.id, ctx.guild.id)

        is_host = False
        for r in rooms:
            if r.host == player.id:
                is_host = True
                break
        if not is_host:
            return (None, settings.get_text('not_host_of_any'))
        
        room = None
        if len(rooms) > 1:
            role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions and ctx.message.role_mentions[0] else None
            string = ' '.join(args).lower()
            rx = re.search(r'\((.*?)\)', string)
            text_filter = rx.group(1) if rx else remove_mentions(string)
            for r in rooms:
                match_channel = ctx.channel.id == r.channel_id if ctx.channel else False
                match_text = text_filter and text_filter in r.activity.lower()
                match_role = role_mention_filter == r.role_id
                if match_channel or match_text or match_role:
                    room = r
                    break
            if not room:
                return (None, settings.get_text('in_multiple_rooms'))
        elif len(rooms) == 1:
            room = rooms[0]
        else:
            return (None, settings.get_text('not_in_room'))

        if room.host != player.id:
            return (None, settings.get_text('not_host_of_room'))
        return (room, None)


    @classmethod
    def get_by_mention(cls, ctx, args):
        rooms = cls.find(guild=ctx.guild.id)
        player_filter = ctx.message.mentions[0].id if ctx.message.mentions else None
        activity_filter = " ".join(args) if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = cls.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = cls.from_query(room_data)
                if player_filter in r.players or r.activity == activity_filter or r.role_id == role_mention_filter:
                    return r
        return None

    @classmethod
    def get_by_role(cls, role_id):
        room_data = cls.find_one(role_id=role_id)
        if room_data:
            return cls.from_query(room_data)
        return None

    @classmethod
    def get_by_any(cls, ctx, args):
        rooms = cls.find(guild=ctx.guild.id)
        player_mention_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
        text_filter = " ".join(args).lower() if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = cls.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = cls.from_query(room_data)

                # for filtering by target player display name
                player_names = []
                for id in r.players:
                    player = ctx.guild.get_member(id)
                    if player:
                        player_names.append(player.display_name.lower())
                        
                if player_mention_filter in r.players or r.activity.lower() == text_filter or text_filter in player_names or r.role_id == role_mention_filter:
                    return r
        return None

    @classmethod
    def player_is_in_any(cls, player_id, guild_id):
        return len(cls.get_player_rooms(player_id, guild_id)) > 0

    @classmethod
    def get_player_rooms(cls, player_id, guild_id):
        rooms = []
        rooms_query = cls.find(guild=guild_id)
        if rooms_query:
            for room_data in rooms_query:
                r = cls.from_query(room_data)
                if player_id in r.players or player_id == r.host:
                    rooms.append(r)
        return rooms

    @classmethod
    def find(cls, **kwargs):
        return db.rooms.find(**kwargs)

    @classmethod
    def find_one(cls, **kwargs):
        return db.rooms.find_one(**kwargs)

    @classmethod
    async def delete_inactive(cls, bot):
        for room_data in cls.find():
            r = cls.from_query(room_data)
            if r.timeout and r.timeout > 0:
                guild = bot.get_guild(r.guild)
                birth_channel = guild.get_channel(r.birth_channel) if guild else None
                channel = guild.get_channel(r.channel_id) if guild else None

                if (channel):
                    history = (await channel.history(limit=1).flatten())
                    if len(history) > 0:
                        last_message = history[0]
                        last_message_datetime = utime(last_message.created_at)
                        voice_channel = guild.get_channel(r.voice_channel_id) if guild else None
                        if voice_channel and len(voice_channel.members) > 0:
                            r.update_active()
                        if last_message_datetime > utime(r.last_active):
                            r.update('last_active', last_message_datetime)

                time_diff = now() - utime(r.last_active)
                if time_diff.total_seconds()/60 >= r.timeout: # timeout is in minutes
                    if guild:
                        await r.disband(guild)
                        if birth_channel:
                            settings = Settings.get_for(guild.id)
                            try:
                                await birth_channel.send(settings.get_text('disband_from_inactivity').format(r.activity))
                            except:
                                pass
                    else:
                        db.rooms.delete(role_id=r.role_id)
                        db.invites.delete(room_id=r.role_id)

    def get_symbols(self):
        symbols = ''
        if self.nsfw:
            symbols += ':underage:'
        if self.lock:
            symbols += ':lock:'
        if symbols:
            symbols += ' '
        return symbols


    def update(self, field, value):
        v = self.unpack_value(value, Room.props[field])
        self.__setattr__(field, v)
        new_dict = {}
        new_dict['role_id'] = self.role_id
        new_dict[field] = value
        db.rooms.update(new_dict, ['role_id'])
        if field != 'last_active':
            asyncio.ensure_future(
                RoomEmbed.update(self) )

    def update_active(self):
        self.last_active = now()
        self.update('last_active', self.last_active)

    async def add_player(self, player):
        s = Settings.get_for(self.guild)
        role = player.guild.get_role(self.role_id)
        channel = player.guild.get_channel(self.channel_id)
        if not channel or not role:
            return (False, s.get_text('retry_error'))
        if player.id in self.players:
            return (False, s.get_text('already_joined'))

        await player.add_roles(role)
        self.players.append(player.id)
        self.update('players', ids_to_str(self.players))
        await channel.edit(topic="({}/{}) {}".format(len(self.players), self.size, self.description))
        return True

    async def remove_player(self, player):
        s = Settings.get_for(self.guild)
        if player.id in self.players:
            role = player.guild.get_role(self.role_id)
            await player.remove_roles(role)
            self.players.remove(player.id)
            self.update('players', ids_to_str(self.players))
            if len(self.players) < 1:
                await self.disband(player.guild)
                return (True, s.get_text('disband_empty_room'))
            return (True, None)
        return (False, None)

    async def disband(self, guild):
        db.rooms.delete(role_id=self.role_id)
        db.invites.delete(room_id=self.role_id)
        asyncio.ensure_future(
            RoomEmbed.destroy_room(self.role_id) )

        role = guild.get_role(self.role_id)
        await try_delete(role)
        channel = guild.get_channel(self.channel_id)
        await try_delete(channel)
        if self.voice_channel_id:
            voice_channel = guild.get_channel(self.voice_channel_id)
            await try_delete(voice_channel)