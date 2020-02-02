import discord
import asyncio
import dataset
import json
import pytz
import re
from random import choice
from datetime import datetime, timedelta
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

def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n

def has_common_element(a, b):
    return set(a) & set(b)