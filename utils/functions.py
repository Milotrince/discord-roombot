import discord
import asyncio
import pytz
import re
from random import choice
from datetime import datetime, timedelta
from database.connect import *
from utils.text import *

# General helper functions

def log(content):
    print('{} {}'.format(datetime.now(), content))

async def logc(content, bot):
    log(content)
    channel_id = os.getenv('LOGGING_CHANNEL_ID')
    guild_id = os.getenv('LOGGING_SERVER_ID')
    if bot and channel_id and guild_id:
        guild = bot.get_guild(int(guild_id))
        if guild:
            channel = guild.get_channel(int(channel_id))
            if channel:
                await channel.send(content)

def load_cog(bot, cog):
    for command in cog.get_commands():
        text = get_text('_commands')[command.name]
        command.update(
            name=text['_name'],
            help='\n'.join(text['_help']),
            aliases=text['_aliases'],
            pass_context=True )
    bot.add_cog(cog)


def now():
    return datetime.now(pytz.utc)

def utime(d):
    return d.replace(tzinfo=pytz.utc)


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

def get_color(color):
    hex_match = re.search('[0-9a-fA-F]{6}', color)
    if hex_match and hex_match.group():
        return discord.Color(int(hex_match.group(), 16))
    if 'teal' in color:
        return discord.Color.teal()
    elif 'green' in color:
        return discord.Color.green()
    elif 'blue' in color:
        return discord.Color.blue()
    elif 'purple' in color:
        return discord.Color.purple()
    elif 'magenta' in color or 'pink' in color:
        return discord.Color.magenta()
    elif 'gold' in color or 'yellow' in color:
        return discord.Color.gold()
    elif 'orange' in color:
        return discord.Color.orange()
    elif 'red' in color:
        return discord.Color.red()
    else:
        return discord.Color(some_color())

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

def bool_to_text(yes):
    return "Yes" if yes else "No"

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

def remove_mentions(args):
    if isinstance(args, list) or isinstance(args, tuple):
        return re.sub(r"<(@!|@&|#)[\d]*>", '', ' '.join(args)).split(' ')
    else:
        return re.sub(r"<(@!|@&|#)[\d]*>", '', args).strip()