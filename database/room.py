from utils.functions import *
from database.settings import *

async def get_rooms_category(guild):
    settings = Settings.get_for(guild.id)
    existing_category = discord.utils.get(guild.categories, name=settings.category_name)
    return existing_category if existing_category else await guild.create_category(settings.category_name)


class Room:
    def __init__(self, role_id, channel_id, voice_channel_id, color, birth_channel, guild,
            lock, activity, description, created, timeout, players, host, size, last_active):
        self.role_id = role_id
        self.channel_id = channel_id
        self.voice_channel_id = voice_channel_id
        self.color = color
        self.birth_channel = birth_channel
        self.guild = guild
        self.lock = lock
        self.activity = activity
        self.description = description
        self.created = created
        self.timeout = timeout
        self.players = players
        self.host = host
        self.size = int(size)
        self.last_active = last_active

        rooms_db.upsert(dict(
            role_id=role_id,
            channel_id=channel_id,
            voice_channel_id=voice_channel_id,
            color=color,
            birth_channel=birth_channel,
            guild=guild,
            lock=lock,
            activity=activity,
            description=description,
            created=created,
            timeout=timeout,
            players=ids_to_str(players),
            host=host,
            size=size,
            last_active=last_active ), ['role_id'])
            
    @classmethod
    def from_message(cls, ctx, args, settings, activity, role, channel, voice_channel):
        guild = ctx.guild.id
        voice_channel_id = voice_channel.id if voice_channel else 0
        color = role.color.value
        birth_channel = ctx.message.channel.id
        lock = settings.room_defaults['lock']
        description = choice(settings.room_defaults['descriptions'])
        created = now()
        timeout = settings.room_defaults['timeout']
        players = []
        host = ctx.message.author.id
        size = settings.room_defaults['size']
        last_active = now()
        return cls(role.id, channel.id, voice_channel_id, color, birth_channel, guild, lock,
                activity, description, created, timeout, players, host, size, last_active)
            
    @classmethod
    def from_query(cls, data):
        role_id = data['role_id']
        channel_id = data['channel_id']
        voice_channel_id = data['voice_channel_id']
        color = data['color']
        birth_channel = data['birth_channel']
        guild = data['guild']
        lock = data['lock'] if 'lock' in data else False
        activity = data['activity']
        description = data['description']
        created = data['created']
        timeout = data['timeout']
        players = str_to_ids(data['players'])
        host = data['host']
        size = data['size']
        last_active = data['last_active']
        return cls(role_id, channel_id, voice_channel_id, color, birth_channel, guild, lock,
                activity, description, created, timeout, players, host, size, last_active)

    @classmethod
    def get_hosted(cls, player_id, guild_id):
        rooms = rooms_db.find(guild=guild_id, host=player_id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
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
                r = Room.from_query(room_data)
                if player_filter in r.players or r.activity == activity_filter or r.role_id == role_mention_filter:
                    return r
        return None

    @classmethod
    def get_by_role(cls, role_id):
        room_data = rooms_db.find_one(role_id=role_id)
        if room_data:
            return Room.from_query(room_data)
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
                r = Room.from_query(room_data)

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
        rooms = rooms_db.find(guild=guild_id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if player_id in r.players or player_id == r.host:
                    return True
        return False


    def get_embed(self, player, footer_action):
        description = discord.Embed.Empty if self.description == '' else self.description
        room_status = get_text('room_status').format(self.size - len(self.players)) if len(self.players) < self.size else get_text('full_room')

        embed = discord.Embed(
            color=self.color,
            description=description,
            timestamp=self.created,
            title="{}{}".format(":lock: " if self.lock else "", self.activity) )
        embed.add_field(
            name="{} ({}/{})".format(get_text('players'), len(self.players), self.size),
            value="<@{}>".format(">, <@".join([str(id) for id in self.players])) )
        embed.add_field(
            name=room_status,
            value=get_text('room_timeout_on').format(self.timeout) if self.timeout > 0 else get_text('room_timeout_off') )
        embed.add_field(
            name=get_text('host'),
            value="<@{}>".format(self.host)),
        embed.add_field(
            name=get_text('channel'),
            value="<#{}>".format(self.channel_id)),
        embed.set_footer(
            text="{} : {}".format(footer_action, player.display_name),
            icon_url=discord.Embed.Empty )
        
        return embed

    def send_embed(self, embed, channel):
        asdf = channel

    def update(self, field, value):
        new_dict = {}
        new_dict['role_id'] = self.role_id
        new_dict[field] = value
        rooms_db.update(new_dict, ['role_id'])

    def update_active(self):
        self.last_active = now()
        self.update('last_active', self.last_active)

    async def add_player(self, player):
        role = player.guild.get_role(self.role_id)
        channel = player.guild.get_channel(self.channel_id)
        if not channel or not role:
            return (False, get_text('retry_error'))
        if player.id in self.players:
            return (False, get_text('already_joined'))

        await player.add_roles(role)
        self.players.append(player.id)
        self.update('players', ids_to_str(self.players))
        await channel.edit(topic="({}/{}) {}".format(len(self.players), self.size, self.description))
        return True

    async def remove_player(self, player):
        if player.id in self.players:
            role = player.guild.get_role(self.role_id)
            await player.remove_roles(role)
            self.players.remove(player.id)
            self.update('players', ids_to_str(self.players))
            if len(self.players) < 1:
                await self.disband(player.guild)
                return (True, get_text('disband_empty_room'))
            return (True, None)
        return (False, None)

    async def disband(self, guild):
        role = guild.get_role(self.role_id)
        rooms_db.delete(role_id=self.role_id)
        await role.delete()

        channel = guild.get_channel(self.channel_id)
        await channel.delete()

        voice_channel = guild.get_channel(int(self.voice_channel_id))
        if voice_channel:
            await voice_channel.delete()
