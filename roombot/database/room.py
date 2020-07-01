from roombot.utils.roomembed import RoomEmbed
from roombot.utils.functions import *
from roombot.database.settings import *
import asyncio

async def get_rooms_category(guild):
    settings = Settings.get_for(guild.id)
    existing_category = discord.utils.get(guild.categories, name=settings.category_name)
    return existing_category if existing_category else await guild.create_category(settings.category_name)


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
        'activity': '',
        'description': '',
        'timeout': 0,
        'created': now(),
        'last_active': now(),
    }

    def __init__(self, data={}, **kwargs):
        data.update(kwargs)
        self.unpack_data(data)
        rooms_db.upsert(self.pack_data(), ['role_id'])
    
    def unpack_data(self, data):
        for (key, value) in self.props.items():
            if key in data and data[key] != None:
                v = self.unpack_value(data[key], value)
                self.__setattr__(key, v)
    
    def unpack_value(self, value, default):
        v = value
        if isinstance(default, list) and isinstance(v, str):
            v = str_to_ids(v)
        elif isinstance(default, int) and not isinstance(v, int):
            v = int(v)
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
    async def create(cls, member, ctx=None, args=None):
        player = member
        guild = member.guild
        settings = Settings.get_for(guild.id)

        if not guild.me.guild_permissions.manage_channels or not guild.me.guild_permissions.manage_roles:
            raise discord.ext.commands.errors.CommandInvokeError("Missing Permissons")

        # check if able to make room
        if settings.allow_multiple_rooms and cls.get_hosted(player.id, guild.id):
            if ctx:
                await ctx.send(settings.get_text('already_is_host'))
            return
        elif not settings.allow_multiple_rooms and cls.player_is_in_any(player.id, guild.id):
            if ctx:
                await ctx.send(settings.get_text('already_in_room'))
            return

        # activity (room name)
        name = player.display_name
        top = player.top_role.name
        bottom = player.roles[1].name if len(player.roles) > 1 else top
        activity = choice(settings.default_names).format(name, top, bottom)
        if ctx:
            if len(args) < 1 and player.activity and player.activity and player.activity.name and len(player.activity.name) > 1:
                activity = player.activity.name
            elif args:
                activity = remove_mentions(" ".join(args))
        activity = activity[0:90].strip()

        # color
        if player.top_role.color != discord.Color.default():
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
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True),
            role: discord.PermissionOverwrite(read_messages=True)
        }
        for accessor in accessors:
            overwrites[accessor] = discord.PermissionOverwrite(read_messages=True)

        # channel
        category = await get_rooms_category(guild)
        channel = await guild.create_text_channel(
            name=activity,
            category=category,
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
            lock=settings.default_lock,
            description=choice(settings.default_descriptions),
            size=settings.default_size,
            timeout=settings.default_timeout,
            created=now(),
            last_active=now()
        )
        await player.add_roles(role)
        await channel.edit(topic="({}/{}) {}".format(len(room.players), room.size, room.description))
        await channel.send(choice(settings.join_messages).format(player.display_name))
        if ctx:
            await RoomEmbed(ctx, room, settings.get_text('new_room')).send()


            
    @classmethod
    def from_query(cls, data):
        return cls(data)

    @classmethod
    def from_message(cls, message):
        for field in message.embeds[0].fields:
            if field.name in get_all_text('channel'):
                channel_id = field.value[2:-1] # removes mention
                room_data = rooms_db.find_one(channel_id=channel_id)
                if room_data:
                    return cls.from_query(room_data)

    @classmethod
    def get_hosted(cls, player_id, guild_id):
        rooms = rooms_db.find(guild=guild_id, host=player_id)
        if rooms:
            for room_data in rooms:
                r = cls.from_query(room_data)
                return r
        return None  

    @classmethod
    def get_by_mention(cls, ctx, args):
        rooms = rooms_db.find(guild=ctx.guild.id)
        player_filter = ctx.message.mentions[0].id if ctx.message.mentions else None
        activity_filter = " ".join(args) if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = rooms_db.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = cls.from_query(room_data)
                if player_filter in r.players or r.activity == activity_filter or r.role_id == role_mention_filter:
                    return r
        return None

    @classmethod
    def get_by_role(cls, role_id):
        room_data = rooms_db.find_one(role_id=role_id)
        if room_data:
            return cls.from_query(room_data)
        return None

    @classmethod
    def get_by_any(cls, ctx, args):
        rooms = rooms_db.find(guild=ctx.guild.id)
        player_mention_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
        text_filter = " ".join(args).lower() if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = rooms_db.find(guild=ctx.guild.id)
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
        rooms_query = rooms_db.find(guild=guild_id)
        if rooms_query:
            for room_data in rooms_query:
                r = cls.from_query(room_data)
                if player_id in r.players or player_id == r.host:
                    rooms.append(r)
        return rooms


    def update(self, field, value):
        v = self.unpack_value(value, Room.props[field])
        self.__setattr__(field, v)
        new_dict = {}
        new_dict['role_id'] = self.role_id
        new_dict[field] = value
        rooms_db.update(new_dict, ['role_id'])
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
        rooms_db.delete(role_id=self.role_id)
        invites_db.delete(room_id=self.role_id)
        asyncio.ensure_future(
            RoomEmbed.destroy_room(self.role_id) )

        role = guild.get_role(self.role_id)
        await try_delete(role)
        channel = guild.get_channel(self.channel_id)
        await try_delete(channel)
        if self.voice_channel_id:
            voice_channel = guild.get_channel(self.voice_channel_id)
            await try_delete(voice_channel)