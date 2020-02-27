from functions import *

async def get_rooms_category(guild):
    settings = Settings.get_for(guild.id)
    existing_category = discord.utils.get(guild.categories, name=settings.category_name)
    return existing_category if existing_category else await guild.create_category(settings.category_name)


class Settings:
    format = {
        'prefix': { "default_value": "r." },
        'timeout': { "default_value": 300 },
        'role_restriction': { "default_value": [] },
        'access_all_rooms_role': { "default_value": [] },
        'respond_to_invalid': { "default_value": True },
        'delete_command_message': { "default_value": False },
        'default_size': { "default_value": 4 },
        'voice_channel': { "default_value": False },
        'bitrate': { "default_value": 64 },
        'category_name': { "default_value": strings['room'] }
    }
   
    def __init__(self, guild_id, prefix, timeout, role_restriction, access_all_rooms_role, respond_to_invalid,
                 delete_command_message, default_size, voice_channel, bitrate, category_name):
        self.guild_id = guild_id
        self.prefix = prefix
        self.timeout = timeout
        self.role_restriction = role_restriction
        self.access_all_rooms_role = access_all_rooms_role 
        self.respond_to_invalid = respond_to_invalid
        self.delete_command_message = delete_command_message
        self.default_size = default_size
        self.voice_channel = voice_channel
        self.bitrate = bitrate 
        self.category_name = category_name

        self.dict = dict(
            guild_id=guild_id,
            prefix=prefix,
            timeout=timeout,
            role_restriction=ids_to_str(role_restriction),
            access_all_rooms_role=ids_to_str(access_all_rooms_role),
            respond_to_invalid=respond_to_invalid,
            delete_command_message=delete_command_message,
            default_size=default_size,
            voice_channel=voice_channel,
            bitrate=bitrate,
            category_name=category_name)

        settings_db.upsert(self.dict, ['guild_id'])

    @classmethod
    def set_strings(cls):
        for setting in cls.format.keys():
            cls.format[setting]['name'] = strings['_name'][setting]
            cls.format[setting]['flags'] = strings['_aliases'][setting]
            cls.format[setting]['description'] = strings['_help'][setting]

    @classmethod
    def get_default_value(cls, key):
        return cls.format[key]['default_value']

    @classmethod
    def get_for(cls, guild_id):
        query = settings_db.find_one(guild_id=guild_id)
        return cls.from_query(query) if query else cls.make_default(guild_id)

    @classmethod
    def from_query(cls, data):
        return cls(
            data['guild_id'],
            data['prefix'] if 'prefix' in data else cls.get_default_value('prefix'),
            data['timeout'] if 'timeout' in data else int(cls.get_default_value('timeout')),
            str_to_ids(data['role_restriction']) if 'role_restriction' in data else cls.get_default_value('role_restriction'),
            str_to_ids(data['access_all_rooms_role']) if 'access_all_rooms_role' in data else cls.get_default_value('access_all_rooms_role'),
            data['respond_to_invalid'] if 'respond_to_invalid' in data else text_to_bool(cls.get_default_value('respond_to_invalid')),
            data['delete_command_message'] if 'delete_command_message' in data else text_to_bool(cls.get_default_value('delete_command_message')),
            data['default_size'] if 'default_size' in data else int(cls.get_default_value('default_size')),
            data['voice_channel'] if 'voice_channel' in data else text_to_bool(cls.get_default_value('voice_channel')),
            data['bitrate'] if 'bitrate' in data else int(cls.get_default_value('bitrate')),
            data['category_name'] if 'category_name' in data else cls.get_default_value('category_name')
        )

    @classmethod
    def make_default(cls, guild_id):
        return cls(guild_id,
            cls.get_default_value('prefix'),
            cls.get_default_value('timeout'),
            cls.get_default_value('role_restriction'),
            cls.get_default_value('access_all_rooms_role'),
            cls.get_default_value('respond_to_invalid'),
            cls.get_default_value('delete_command_message'),
            cls.get_default_value('default_size'),
            cls.get_default_value('voice_channel'),
            cls.get_default_value('bitrate'),
            cls.get_default_value('category_name'))

    def set(self, ctx, field, value):
        result = (True, None)
        parsed_value = value
        if field == 'prefix':
            max_char_length = 5
            if len(value) > max_char_length:
                result = (False, strings['prefix_too_long'].format(max_char_length))
        elif field == 'timeout':
            try:
                parsed_value = int(value)
            except ValueError:
                parsed_value = False
        elif field == 'default_size' or field == 'bitrate':
            try:
                parsed_value = int(value)
            except ValueError:
                result = (False, strings['need_integer'])
        elif field == 'respond_to_invalid' or field == 'delete_command_message' or field == 'voice_channel':
            parsed_value = text_to_bool(value)
        elif field == 'role_restriction' or field == 'access_all_rooms_role':
            roles = []
            for word in value.split():
                role_id = int( ''.join(re.findall(r'\d*', word)) )
                log(role_id)
                roles.append(role_id)
            parsed_value = ids_to_str(roles) 
        elif field == 'category_name':
            pass
        else:
            result = (False, ['require_flags'])

        if field == 'default_size':
            parsed_value = clamp (parsed_value, 0, 100)
        elif field == 'bitrate':
            parsed_value = clamp (parsed_value, 8, int(ctx.guild.bitrate_limit/1000))

        (success, message) = result
        if (success):
            result = (True, strings['settings_success'].format(field, parsed_value))
            self.update(field, parsed_value)
        return result

    def update(self, field, value):
        new_dict = {}
        new_dict['guild_id'] = self.guild_id
        new_dict[field] = value
        settings_db.update(new_dict, ['guild_id'])

    def get(self, field):
        return self.dict[field]
        


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
        """Create a Room from a message"""
        guild = ctx.guild.id
        voice_channel_id = voice_channel.id if voice_channel else 0
        color = role.color.value
        birth_channel = ctx.message.channel.id
        lock = False
        description = choice(strings['default_room_descriptions'])
        created = datetime.now(pytz.utc)
        timeout = settings.timeout
        players = []
        host = ctx.message.author.id
        size = settings.default_size
        last_active = datetime.now(pytz.utc)
        return cls(role.id, channel.id, voice_channel_id, color, birth_channel, guild, lock,
                activity, description, created, timeout, players, host, size, last_active)
            
    @classmethod
    def from_query(cls, data):
        """Create a Room from a query"""
        role_id = data['role_id']
        channel_id = data['channel_id']
        voice_channel_id = data['voice_channel_id']
        color = data['color']
        birth_channel = data['birth_channel']
        guild = data['guild']
        lock = data['lock']
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
        """Returns the player's hosted room if available."""
        rooms = rooms_db.find(guild=guild_id, host=player_id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                return r
        return None  

    def get_embed(self, player, footer_action):
        """Generate a discord.Embed for this room"""
        description = discord.Embed.Empty if self.description == '' else self.description
        room_status = strings['room_status'].format(self.size - len(self.players)) if len(self.players) < self.size else strings['full_room']

        embed = discord.Embed(
            color=self.color,
            description=description,
            timestamp=self.created,
            title="{}{}".format(":lock: " if self.lock else "", self.activity) )
        embed.add_field(
            name="{} ({}/{})".format(strings['players'], len(self.players), self.size),
            value="<@{}>".format(">, <@".join([str(id) for id in self.players])) )
        embed.add_field(
            name=room_status,
            value=strings['room_timeout_on'].format(self.timeout) if self.timeout else strings['room_timeout_off'] )
        embed.add_field(
            name=strings['host'],
            value="<@{}>".format(self.host)),
        embed.set_footer(
            text="{} : {}".format(footer_action, player.display_name),
            icon_url=discord.Embed.Empty )
        
        return embed

    def update(self, field, value):
        new_dict = {}
        new_dict['role_id'] = self.role_id
        new_dict[field] = value
        rooms_db.update(new_dict, ['role_id'])

    def update_active(self):
        self.last_active = datetime.now(pytz.utc)
        self.update('last_active', self.last_active)

    async def add_player(self, player):
        """Add a player to this room"""
        if player.id not in self.players:
            role = player.guild.get_role(self.role_id)
            channel = player.guild.get_channel(self.channel_id)

            if not channel or not role:
                return False

            await player.add_roles(role)
            self.players.append(player.id)
            self.update('players', ids_to_str(self.players))

            await channel.edit(topic="({}/{}) {}".format(len(self.players), self.size, self.description))

        return True

    async def remove_player(self, player):
        """Remove a player from this room"""
        if player.id in self.players:
            role = player.guild.get_role(self.role_id)
            await player.remove_roles(role)
            self.players.remove(player.id)
            self.update('players', ids_to_str(self.players))
            return True
        return False

    async def disband(self, guild):
        """Delete room"""
        role = guild.get_role(self.role_id)
        rooms_db.delete(role_id=self.role_id)
        await role.delete()

        channel = guild.get_channel(self.channel_id)
        await channel.delete()

        voice_channel = guild.get_channel(int(self.voice_channel_id))
        if voice_channel:
            await voice_channel.delete()
