from roombot.database.db import RoomBotDatabase
from roombot.utils.functions import get_default_colors, get_color, text_to_bool, ids_to_str, str_to_ids, clamp, is_number, strip_list
from roombot.utils.text import langs, get_text
from collections import OrderedDict
import os
import re

db = RoomBotDatabase()

class Settings:
    defaults = {
        'language': 'en',
        'prefix': 't.' if os.getenv('ENV') == 'development' else 'r.',
        'allow_multiple_rooms': False,
        'creation_channel': 0,
        'voice_creation_channel': 0,
        'allowed_host_commands': ['activity', 'color', 'description', 'host', 'kick', 'lock', 'nsfw', 'size', 'timeout', 'voice_channel', 'grant_permissions', 'remove_permissions', 'reset_permissions'],
        'respond_to_invalid': True,
        'delete_command_message': False,
        'role_restriction': [],
        'access_all_rooms_role': [],
        'bitrate': 64,
        'category_name': '',
        'use_role_color': True,
        'default_names': [],
        'default_descriptions': [],
        'default_colors': get_default_colors(),
        'default_timeout': 120,
        'default_size': 4,
        'default_voice_channel': False,
        'default_lock': False,
        'default_nsfw': False,
        'join_messages': [],
        'leave_messages': [],
    }
   
    def __init__(self, data={}, **kwargs):
        data = { **data, **kwargs}
        _data = self.unpack_data(data)
        self.set_programmatic_defaults(_data)
        self.guild_id = data['guild_id']
        _data['guild_id'] = self.guild_id
        db.settings.upsert(self.pack_data(_data), ['guild_id'])

    def set_programmatic_defaults(self, data):
        for (key, value) in data.items():
            if key in self.defaults.keys() and key != 'guild_id':
                if isinstance(self.defaults[key], list):
                    value = strip_list(value)
                self.__setattr__(key, value)
        if self.default_descriptions == []:
            self.default_descriptions = self.get_text('default_room_descriptions')
        if self.default_names == []:
            self.default_names = self.get_text('default_room_names')
        if self.join_messages == []:
            self.join_messages = self.get_text('join_messages')
        if self.leave_messages == []:
            self.leave_messages = self.get_text('leave_messages')
        if self.category_name == '':
            self.category_name = self.get_text('room')
        if self.allowed_host_commands == []:
            self.allowed_host_commands = self.defaults['allowed_host_commands']

    def get_text(self, key):
        return get_text(key, self.language)


    @classmethod
    def unpack_data(cls, data):
        unpacked = {}
        for (key, default) in cls.defaults.items():
            value = default
            if key in data and data[key] != None:
                v = data[key]
                if is_number(default):
                    value = int(v)
                elif isinstance(default, str):
                    value = str(v)
                elif isinstance(default, bool):
                    value = text_to_bool(v) if isinstance(v, str) else bool(v)
                elif isinstance(default, list) and isinstance(v, str):
                    if key in ['role_restriction', 'access_all_rooms_role']:
                        value = str_to_ids(v)
                    else:
                        value = re.split('[,]+', v)
            unpacked[key] = value
        return unpacked

    @classmethod
    def pack_data(cls, data):
        packed = {'guild_id': data['guild_id']}
        for (key, default) in cls.defaults.items():
            value = default
            if key in data:
                v = data[key]
                if isinstance(default, bool):
                    value = bool(v)
                elif isinstance(default, list):
                    value = ids_to_str(v)
                else:
                    value = str(v)
            packed[key] = value
        return packed


    @classmethod
    def get_default_value(cls, key):
        return cls.defaults[key]

    @classmethod
    def get_for(cls, guild_id):
        query = db.settings.find_one(guild_id=guild_id)
        return cls.from_query(query) if query else cls.make_default(guild_id)

    @classmethod
    def from_query(cls, data):
        return cls(data)

    @classmethod
    def make_default(cls, guild_id):
        return cls(guild_id=guild_id)

    @classmethod
    async def delete_inactive(cls, bot):
        print("in settings delete")
        for s_data in db.settings.all():
            s = cls.from_query(s_data)

            guild = bot.get_guild(s.guild_id)
            if guild == None:
                print('deleting')
                db.rooms.delete(guild=s.guild_id)
                db.invites.delete(guild=s.guild_id)
                db.settings.delete(guild=s.guild_id)

    def set(self, ctx, field, value):
        result = (True, None)
        parsed_value = value
        if field not in self.defaults.keys():
            return (False, self.get_text('require_flags'))
        default = self.defaults[field]

        if field in ['voice_creation_channel', 'creation_channel']:
            parsed_value = 0
            channels = ctx.guild.voice_channels
            for c in channels:
                if len(value) > 1 and value in c.name or value == str(c.id):
                    parsed_value = c.id
        elif is_number(default):
            try:
                parsed_value = int(value)
            except ValueError:
                parsed_value = -1

            if field in ['size', 'default_size']:
                parsed_value = clamp(parsed_value, 2, 999)
            elif field == 'bitrate':
                parsed_value = clamp(parsed_value, 8, int(ctx.guild.bitrate_limit/1000))
            elif field == 'timeout':
                parsed_value = clamp(parsed_value, -1, 999)

        elif isinstance(default, bool):
            parsed_value = text_to_bool(value)

        elif isinstance(default, list):
            if field in ['role_restriction', 'access_all_rooms_role']:
                roles = []
                for word in re.split('[,\s]+', value):
                    try:
                        r = re.search(r'\d+', word)
                        if r:
                            role_id = int(r.group())
                            roles.append(role_id)
                    except ValueError:
                        result = (False, self.get_text('should_use_mentions'))
                parsed_value = ids_to_str(roles) 
            elif field == 'default_colors':
                colors = []
                for s in re.split('[,\s]+', value):
                    color = get_color(s, return_default=False)
                    if color:
                        colors.append(str(color.value))
                parsed_value = ','.join(colors)
            elif field == 'allowed_host_commands':
                commands = []
                for c in re.split('[,\s]+', value):
                    if c in default and c not in commands:
                        commands.append(c)
                if commands == []:
                    commands = default
                parsed_value = ','.join(commands)
            else:
                messages = []
                for s in re.split('[,]+', value):
                    m = s.strip().replace('__', '{0}')
                    if len(m) > 0:
                        messages.append(m)
                parsed_value = ','.join(messages)

        elif isinstance(default, str):
            if field == 'prefix':
                max_char_length = 5
                if len(value) > max_char_length:
                    result = (False, self.get_text('prefix_too_long').format(max_char_length))
            elif field == 'language':
                parsed_value = value[:2].lower()
                if parsed_value not in langs:
                    result = (False, self.get_text('language_not_exist').format(parsed_value))
            elif field == 'category_name':
                parsed_value = value[:99]

        (success, message) = result
        if (success):
            is_string = isinstance(parsed_value, str)
            text_value = parsed_value if not is_string or (is_string and len(parsed_value) > 0) else 'None'
            self.update(field, parsed_value)
            result = (True, self.get_text('set_value').format(field, text_value))
        return result

    def update(self, field, value):
        if field in self.defaults.keys():
            self.__setattr__(field, value)
            new_dict = {'guild_id': self.guild_id}
            new_dict[field] = value
            db.settings.update(new_dict, ['guild_id'])

    def get(self, field):
        return getattr(self, field)