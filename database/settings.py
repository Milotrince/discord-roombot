from utils.functions import *

class Settings:
    defaults = {
        'prefix': "r.",
        'timeout': 120,
        'role_restriction': [],
        'access_all_rooms_role': [],
        'respond_to_invalid': True,
        'delete_command_message': False,
        'default_size': 4,
        'voice_channel': False,
        'bitrate': 64,
        'category_name': get_text('room')
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
    def get_default_value(cls, key):
        return cls.defaults[key]

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
                result = (False, get_text('prefix_too_long').format(max_char_length))
        elif field in ['size', 'default_size', 'bitrate', 'timeout']:
            try:
                parsed_value = int(value)
            except ValueError:
                parsed_value = -1
        elif field in ['respond_to_invalid', 'delete_command_message', 'voice_channel']:
            parsed_value = text_to_bool(value)
        elif field in ['role_restriction', 'access_all_rooms_role']:
            roles = []
            for word in value.split():
                role_id = int( ''.join(re.findall(r'\d*', word)) )
                roles.append(role_id)
            parsed_value = ids_to_str(roles) 
        elif field == 'category_name':
            pass
        else:
            result = (False, ['require_flags'])

        if field in ['size', 'default_size']:
            parsed_value = clamp (parsed_value, 2, 999)
        elif field == 'bitrate':
            parsed_value = clamp (parsed_value, 8, int(ctx.guild.bitrate_limit/1000))
        elif field == 'timeout':
            parsed_value = clamp (parsed_value, -1, 999)

        (success, message) = result
        if (success):
            result = (True, get_text('settings_success').format(field, parsed_value))
            self.update(field, parsed_value)
        return result

    def update(self, field, value):
        new_dict = {}
        new_dict['guild_id'] = self.guild_id
        new_dict[field] = value
        settings_db.update(new_dict, ['guild_id'])

    def get(self, field):
        return self.dict[field]