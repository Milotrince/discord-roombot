from utils.functions import *
from pprint import pprint

class Settings:
    defaults = {
        'prefix': 'r.',
        'role_restriction': [],
        'access_all_rooms_role': [],
        'respond_to_invalid': True,
        'delete_command_message': False,
        'bitrate': 64,
        'category_name': '',
        'room_defaults': {
            'timeout': 120,
            'size': 4,
            'voice_channel': False,
            'descriptions': [],
            'names': [],
            'colors': get_default_colors(),
            'lock': False
        },
        'join_messages': [],
        'leave_messages': [],
        'allow_multiple_rooms': False,
        'allowed_host_commands': [],
        'language': 'en'
    }
   
    def __init__(self, data):
        _data = self.unpack_data(data, self.defaults)
        _data['guild_id'] = data['guild_id']
        self.set_programmatic_defaults(_data)
        settings_db.upsert(self.pack_data(_data, self.defaults), ['guild_id'])

    def set_programmatic_defaults(self, data):
        for (key, value) in data.items():
            self.__setattr__(key, value)
        if self.room_defaults['descriptions'] == []:
            self.room_defaults['descriptions'] = self.get_text('default_room_descriptions')
        if self.room_defaults['names'] == []:
            self.room_defaults['names'] = self.get_text('default_room_names')
        if self.join_messages == []:
            self.join_messages = self.get_text('join_messages')
        if self.leave_messages == []:
            self.leave_messages = self.get_text('leave_messages')
        if self.category_name == '':
            self.category_name = self.get_text('room')
        if self.allowed_host_commands == []:
            # TODO: allowed_host_commands
            pass

    def get_text(self, key):
        return get_text(key, self.language)


    @classmethod
    def unpack_data(cls, data, defaults):
        unpacked = {}
        for (key, default) in defaults.items():
            value = default
            if key in data and data[key] != None:
                v = data[key]
                if is_number(default):
                    value = int(v)
                elif isinstance(default, str):
                    value = str(v)
                elif isinstance(default, bool):
                    value = text_to_bool(v) if isinstance(v, str) else bool(v)
                elif isinstance(default, list):
                    value = str_to_ids(v) if isinstance(v, str) else v
                elif isinstance(default, dict):
                    if isinstance(v, str):
                        try:
                            value = json.loads(v)
                        except:
                            pass
            unpacked[key] = value
        return unpacked

    @classmethod
    def pack_data(cls, data, defaults):
        packed = {'guild_id': data['guild_id']}
        for (key, default) in defaults.items():
            value = default
            if key in data:
                v = data[key]
                if isinstance(default, bool):
                    value = bool(v)
                elif isinstance(default, list):
                    value = ids_to_str(v)
                elif isinstance(default, dict):
                    value = json.dumps(v)
                else:
                    value = str(v)
            packed[key] = value
        return packed


    @classmethod
    def get_default_value(cls, key):
        return cls.defaults[key]

    @classmethod
    def get_for(cls, guild_id):
        query = settings_db.find_one(guild_id=guild_id)
        return cls.from_query(query) if query else cls.make_default(guild_id)

    @classmethod
    def from_query(cls, data):
        return cls(data)

    @classmethod
    def make_default(cls, guild_id):
        return cls({ 'guild_id': guild_id })

    def set(self, ctx, field, value):
        result = (True, None)
        parsed_value = value
        if field not in self.defaults.keys():
            return (False, self.get_text('require_flags'))
        elif field in ['allowed_host_commands', 'language', 'room_defaults', 'allow_multiple_rooms', 'join_messages', 'leave_messages']:
            return (False, self.get_text('coming_soon').format(self.prefix))
        default = self.defaults[field]

        if is_number(default):
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
                for word in re.split('[,\w]*', value):
                    try:
                        role_id = int( ''.join(re.findall(r'\d*', word)) )
                        roles.append(role_id)
                    except ValueError:
                        result = (False, get_text('should_use_mentions'))
                parsed_value = ids_to_str(roles) 
            else:
                pass

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
            result = (True, self.get_text('settings_success').format(field, text_value))
            self.update(field, parsed_value)
        return result

    def update(self, field, value):
        new_dict = {}
        new_dict['guild_id'] = self.guild_id
        new_dict[field] = value
        settings_db.update(new_dict, ['guild_id'])

    def get(self, field):
        return getattr(self, field)