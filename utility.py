from room import *

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
    """Returns (flags, args without flags). Flags are words starting with -"""
    nonflags = list(args)
    flags = []

    for arg in list(args):
        if arg.startswith('-'):
            flags.append(arg[1:])
            nonflags.remove(arg)

    return (flags, nonflags)


def get_hosted_room(player_id, guild_id):
    """Returns the player's hosted room if available."""
    rooms_data = rooms.find(guild=guild_id, host=player_id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            return r
    return None

def iter_len(iterator):
    return sum(1 for _ in iterator)


def log(content):
    print('{} {}'.format(datetime.now(), content))


def join_message(name):
    return choice([
        "Do not fear! {} is here!",
        "{} joined the room.",
        "{} just stepped inside.",
        "Be nice to {}, ok everyone?",
        "The adventurer {} has joined your party.",
        "A {} has spawned!",
        "A wild {} appears!" ]).format(name)

def create_message(name):
    return choice([
        "Welcome to your room, {}.",
        "{}, you are now the proud owner of this room.",
        "Hi {}! A very cool room, this is.",
        "A very nice and roomy room I made for you, {}.",
        "So.. are you gonna have parties in this place {}?" ]).format(name)

def invite_message(player_name, room_name):
    return choice([
        "You have been cordially invited to join `{1}`.",
        "{0} wants YOU to join `{1}`.",
        "A wild invite appeared!",
        "Come join {0}'s room!",
        "Hop into `{1}`!" ]).format(player_name, room_name)

