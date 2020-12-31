import discord
import pytz
import re
from random import choice
from datetime import datetime, timedelta
from roombot.utils.text import langs, get_text, get_all_text


# discord =============

def load_cog(bot, cog):
    for command in cog.get_commands():
        aliases = []
        command.update(
            aliases=get_aliases(command.name),
            pass_context=True )
    bot.add_cog(cog)

def get_aliases(command_name):
    aliases = []
    for lang in langs:
        text = get_text('_commands', lang=lang)[command_name]
        aliases += text['_aliases']
    return list(set(aliases))

def remove_mentions(args):
    if isinstance(args, list) or isinstance(args, tuple):
        return re.sub(r"<(@!|@&|#)[\d]*>", '', ' '.join(args)).split(' ')
    else:
        return re.sub(r"<(@!|@&|#)[\d]*>", '', args).strip()

def clean_args(args):
    s = re.sub(r'\((.*?)\)', '', remove_mentions(' '.join(args))).strip()
    return re.sub(r'\s+', ' ', s).split(' ')

def get_target(guild, text, member=True, role=True):
    text = text.lower()
    rx = re.search('\d{14,}', text)
    id = rx.group() if rx else None
    if member:
        if id:
            p = guild.get_member(int(id))
            if p:
                return p
        for p in guild.members:
            if text in p.display_name.lower() or text in p.name.lower():
                return p
    if role:
        if id:
            r = guild.get_role(int(id))
            if r:
                return r
        for r in guild.roles:
            if text in r.name.lower():
                return r

async def get_rooms_category(guild, settings):
    existing_category = discord.utils.get(guild.categories, name=settings.category_name)
    if existing_category:
        return existing_category
    else:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True),
        }
        return await guild.create_category(settings.category_name, overwrites=overwrites)

async def try_delete(discord_object):
    try:
        await discord_object.delete()
    except:
        pass


# time =============

def now():
    return datetime.now(pytz.utc)

def utime(d):
    return d.replace(tzinfo=pytz.utc)


# colors =============

def get_default_colors():
    return [ c.value for c in [
        discord.Color.teal(),
        discord.Color.green(),
        discord.Color.blue(),
        discord.Color.purple(),
        discord.Color.magenta(),
        discord.Color.gold(),
        discord.Color.orange(),
        discord.Color.red()] ]

def some_color():
    return choice(get_default_colors())

def get_color(color, return_default=True):
    hex_match = re.search('[0-9a-fA-F]{6}', color)
    if hex_match and hex_match.group():
        return discord.Color(int(hex_match.group(), 16))
    elif color in get_all_text('red'):
        return discord.Color.red()
    elif color in get_all_text('orange'):
        return discord.Color.orange()
    elif color in get_all_text('yellow'):
        return discord.Color.gold()
    elif color in get_all_text('green'):
        return discord.Color.green()
    elif color in get_all_text('teal'):
        return discord.Color.teal()
    elif color in get_all_text('blue'):
        return discord.Color.blue()
    elif color in get_all_text('purple'):
        return discord.Color.purple()
    elif color in get_all_text('pink'):
        return discord.Color.magenta()
    elif return_default:
        return discord.Color(some_color())
    else:
        return None



# other =============

def pop_flags(args):
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
    return text.lower() in get_text('True')

def iter_len(iterator):
    return sum(1 for _ in iterator)

def ids_to_str(ids, seperator=','):
    return seperator.join([ str(id) for id in ids ]) if ids else ''

def str_to_ids(s):
    try:
        return [ int(id) for id in s.split(',') ] if s else []
    except ValueError:
        return s.split(',') if s else []

def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n

def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def has_common_element(a, b):
    return set(a) & set(b)

def strip_list(_list):
    l = []
    for el in _list:
        if isinstance(el, str) and len(el) < 1:
            pass
        else:
            l.append(el)
    return l
