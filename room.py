import discord
import asyncio
import pytz
import dataset
import json
from random import choice
from datetime import datetime, timedelta

# Get database
db = dataset.connect('sqlite:///database.db')
rooms_db = db.get_table('rooms', primary_id='role_id')
settings_db = db.get_table('settings', primary_id='guild_id')

# Get json file of strings
with open('config/strings.json', 'r') as strings_file:  
    strings = json.load(strings_file)

# General helper functions
def log(content):
    print('{} {}'.format(datetime.now(), content))

def some_color():
    """Returns a random standard Discord color"""
    return choice([
        discord.Color.teal(),
        discord.Color.green(),
        discord.Color.blue(),
        discord.Color.purple(),
        discord.Color.magenta(),
        discord.Color.gold(),
        discord.Color.orange(),
        discord.Color.red() ])

def get_color(color):
    if color == 'teal':
        return discord.Color.teal()
    elif color == 'green':
        return discord.Color.green()
    elif color == 'blue':
        return discord.Color.blue()
    elif color == 'purple':
        return discord.Color.purple()
    elif color == 'magenta' or color == 'pink':
        return discord.Color.magenta()
    elif color == 'gold' or color == 'yellow':
        return discord.Color.gold()
    elif color == 'orange':
        return discord.Color.orange()
    elif color == 'red':
        return discord.Color.red()
    else:
        return some_color()

def pop_flags(args):
    """Returns (flags, args for flag). Flags are words starting with -"""
    split_on_flags = ' '.join(list(args)).split('-')
    del split_on_flags[0]
    flags = []
    flag_args = []
    for flag_group in split_on_flags:
        flag_group_list = flag_group.split(' ')
        flag = flag_group_list.pop(0)
        flags.append(flag)
        flag_args.append(' '.join(flag_group_list))
    return (flags, flag_args)

def text_to_bool(text):
    return text.lower() in strings['True']

def bool_to_text(yes):
    return "Yes" if yes else "No"

def iter_len(iterator):
    return sum(1 for _ in iterator)

def ids_to_str(ids, seperator=','):
    """Turn a list of ints into a database inputable string"""
    return seperator.join([ str(id) for id in ids ])

def str_to_ids(s):
    """Turn a string of comma seperated ints from a database into a list of ints"""
    return [ int(id) for id in s.split(',') ] if s else []

async def get_rooms_category(guild):
    settings = Settings.get_for(guild.id)
    existing_category = discord.utils.get(guild.categories, name=settings.category_name)
    return existing_category if existing_category else await guild.create_category(settings.category_name)


class Settings:
    format = dict(
        prefix={
            "description": strings['prefix_description'],
            "flags": ["prefix"],
            "default_value": "r." },
        timeout={
            "description": strings['timeout_description'],
            "flags": ["timeout"],
            "default_value": 300 },
        respond_to_invalid={
            "description": strings['respond_to_invalid_description'],
            "flags": ["respond_to_invalid", "rti"],
            "default_value": True },
        delete_command_message={
            "description": strings['delete_command_message_description'],
            "flags": ["delete_command_message", "dcm"],
            "default_value": False },
        size={
            "description": strings['size'],
            "flags": ["size"],
            "default_value": 4 },
        voice_channel={
            "description": strings['voice_channel_description'],
            "flags": ["voice_channel", "vc"],
            "default_value": False },
        category_name={
            "description": strings['category_name_description'],
            "flags": ["category_name", "category"],
            "default_value": strings['room'] })
    
    def __init__(self, guild_id, prefix, timeout, respond_to_invalid,
                 delete_command_message, size, voice_channel, category_name):
        self.guild_id = guild_id
        self.prefix = prefix
        self.timeout = timeout
        self.respond_to_invalid = respond_to_invalid
        self.delete_command_message = delete_command_message
        self.size = size
        self.voice_channel = voice_channel
        self.category_name = category_name

        self.dict = dict(
            guild_id=guild_id,
            prefix=prefix,
            timeout=timeout,
            respond_to_invalid=respond_to_invalid,
            delete_command_message=delete_command_message,
            size=size,
            voice_channel=voice_channel,
            category_name=category_name)

        settings_db.upsert(self.dict, ['guild_id'])

    @classmethod
    def get_default_value(cls, key):
        return cls.format[key]['default_value']

    @classmethod
    def get_for(cls, guild_id):
        query = settings_db.find_one(guild_id=guild_id)
        return cls.from_query(query) if query else cls.make_default(guild_id)

    @classmethod
    def from_query(cls, data):
        guild_id = data['guild_id']
        prefix = data['prefix'] if 'prefix' in data else cls.get_default_value('prefix')
        timeout = data['timeout'] if 'timeout' in data else int(cls.get_default_value('timeout'))
        respond_to_invalid = data['respond_to_invalid'] if 'respond_to_invalid' in data else text_to_bool(cls.get_default_value('respond_to_invalid'))
        delete_command_message = data['delete_command_message'] if 'delete_command_message' in data else text_to_bool(cls.get_default_value('delete_command_message'))
        size = data['size'] if 'size' in data else int(cls.get_default_value('size'))
        voice_channel = data['voice_channel'] if 'voice_channel' in data else text_to_bool(cls.get_default_value('voice_channel'))
        category_name = data['category_name'] if 'category_name' in data else cls.get_default_value('category_name')
        return cls(guild_id, prefix, timeout, respond_to_invalid,
                 delete_command_message, size, voice_channel, category_name)                 

    @classmethod
    def make_default(cls, guild_id):
        return cls(guild_id,
            cls.get_default_value('prefix'),
            cls.get_default_value('timeout'),
            cls.get_default_value('respond_to_invalid'),
            cls.get_default_value('delete_command_message'),
            cls.get_default_value('size'),
            cls.get_default_value('voice_channel'),
            cls.get_default_value('category_name'))

    def set(self, field, value):
        result = (None, None)
        parsed_value = value
        if field == 'prefix':
            if len(value) < 3:
                result = (True, "Set prefix to `{}`.".format(value))
            else:
                result = (False, "Prefix is too long.")
        elif field == 'timeout':
            try:
                parsed_value = int(value)
                result = (True, "Set timeout to `{}` minutes.".format(value))
            except ValueError:
                result = (False, "Timeout must be a whole number (in minutes).")
        elif field == 'respond_to_invalid':
            parsed_value = text_to_bool(value)
            bool_message = "" if text_to_bool(value) else "not "
            result = (True, "Ok, I will {}respond to invalid commands.".format(bool_message))
        elif field == 'delete_command_message':
            parsed_value = text_to_bool(value)
            bool_message = "" if text_to_bool(value) else "not "
            result = (True, "Ok, I will {}delete command messages.".format(bool_message))
        elif field == 'size':
            try:
                parsed_value = min(abs(int(value)), 100)
                result = (True, "Set default room size to {}.".format(parsed_value))
            except ValueError:
                result = (False, "Default room size must be a whole number.")
        elif field == 'voice_channel':
            parsed_value = text_to_bool(value)
            bool_message = "" if text_to_bool(value) else "not "
            result = (True, "Ok, I will {}automatically create a voice channel on room creation.".format(bool_message))
        elif field == 'category_name':
            result = (True, "Set category name to `{}`".format(value))
        else:
            result = (False, "Invalid field.")

        (success, message) = result
        if (success):
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
    def __init__(self, role_id, channel_id, voice_channel_id, color, birth_channel,
                 guild, activity, description, created, timeout, players, host, size, last_active):
        self.role_id = role_id
        self.channel_id = channel_id
        self.voice_channel_id = voice_channel_id
        self.color = color
        self.birth_channel = birth_channel
        self.guild = guild
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
        description = choice(strings['default_room_descriptions'])
        created = datetime.now(pytz.utc)
        timeout = settings.timeout
        players = []
        host = ctx.message.author.id
        size = settings.size
        last_active = datetime.now(pytz.utc)
        return cls(role.id, channel.id, voice_channel_id, color, birth_channel,
                   guild, activity, description, created, timeout, players, host, size, last_active)
            
    @classmethod
    def from_query(cls, data):
        """Create a Room from a query"""
        role_id = data['role_id']
        channel_id = data['channel_id']
        voice_channel_id = data['voice_channel_id']
        color = data['color']
        birth_channel = data['birth_channel']
        guild = data['guild']
        activity = data['activity']
        description = data['description']
        created = data['created']
        timeout = data['timeout']
        players = str_to_ids(data['players'])
        host = data['host']
        size = data['size']
        last_active = data['last_active']
        return cls(role_id, channel_id, voice_channel_id, color, birth_channel,
                   guild, activity, description, created, timeout, players, host, size, last_active)

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
            title=self.activity )
        embed.add_field(
            name="{} ({}/{})".format(strings['players'], len(self.players), self.size),
            value="<@{}>".format(">, <@".join([str(id) for id in self.players])) )
        embed.add_field(
            name=room_status,
            value=strings['room_status_description'] )
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
