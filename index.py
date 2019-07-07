import asyncio
from discord.ext import commands
from room import *

print("""
 _____               _____ _____ _____ 
| __  |___ ___ _____| __  |     |_   _|
|    -| . | . |     | __ -|  |  | | |  
|__|__|___|___|_|_|_|_____|_____| |_|
""")


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


# Define bot
bot = commands.Bot(command_prefix=config['prefix'], case_insensitive=True)
bot.remove_command('help')
discord_blue = discord.Color.from_rgb(114, 137, 218)


@bot.event
async def on_ready():
    """Fired when bot comes online"""
    print('{} is online!'.format(bot.user.name))
    await bot.change_presence(activity=discord.Game(name='the waiting game'))


@bot.event
async def on_disconnect():
    """Fired when bot goes offline"""
    print('{} has disconnected...'.format(bot.user.name))


@bot.command(aliases=['n', 'create', 'start'])
async def new(ctx, *args):
    """Make a new room (uses current activity or input)."""
    activity = None
    player = ctx.message.author

    if not args and player.activity:
        activity = player.activity.name
    else:
        activity = " ".join(args)
    
    if not activity:
        return await ctx.send('Please specify the room activity (or start doing something).')
    if not ctx.guild.me.guild_permissions.manage_channels or not ctx.guild.me.guild_permissions.manage_roles:
        raise discord.ext.commands.errors.CommandInvokeError("Missing Permissons")

    rooms_data = rooms.find(guild=ctx.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player.id in r.players:
                return await ctx.send("You are already in a room.")
            if r.activity == activity:
                activity += " ({})".format(player.name)
                
    role = await player.guild.create_role(
        name="Room - " + activity,
        color=some_color(),
        hoist=True,
        mentionable=True )
    existing_category = discord.utils.get(player.guild.categories, name='Rooms')
    category = existing_category if existing_category else await player.guild.create_category('Rooms')
    channel = await player.guild.create_text_channel(activity, category=category, overwrites={
        player.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        player.guild.me: discord.PermissionOverwrite(read_messages=True),
        role: discord.PermissionOverwrite(read_messages=True) })

    new_room = Room.from_message(activity, ctx, args, role.id, channel.id, role.color)
    new_room.update_active()
    success = await new_room.add_player(player)
    if success:
        emb = new_room.get_embed(player.guild)
        await channel.send("Welcome to your room, {}.".format(player.display_name))
        return await ctx.send(embed=emb)
    return await ctx.send("There was an error. Please try again.")


@bot.command(aliases=['j'])
async def join(ctx, *args):
    """Join a room (by activity or player)."""
    if len(args) < 1:
        return await ctx.send("Please specify a room by activity or player.")
    user_mention_filter = ctx.message.mentions[0].id if ctx.message.mentions else None
    role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None
    text_filter = " ".join(args).lower() if args else None

    rooms_data = rooms.find(guild=ctx.guild.id)
    if rooms_data:
        room_match = None
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if ctx.message.author.id in r.players:
                return await ctx.send("You are already in a room.")

            player_names = []
            for id in r.players:
                player = ctx.guild.get_member(id)
                if player:
                    player_names.append(player.display_name.lower())

            if r.activity.lower() == text_filter or text_filter in player_names or user_mention_filter in r.players or role_mention_filter == r.role_id:
                room_match = r
                
        if room_match:
            room_match.update_active()
            player = ctx.message.author
            if await room_match.add_player(player):
                await ctx.send(embed=room_match.get_embed(player.guild))
                room_channel = ctx.guild.get_channel(room_match.channel_id)
                join_message = choice([
                    "Do not fear! {} is here!",
                    "{} joined the room.",
                    "{} just stepped inside.",
                    "Be nice to {}, ok everyone?",
                    "The adventurer {} has joined your party.",
                    "A {} has spawned!",
                    "A wild {} appears!" ])
                await room_channel.send(join_message.format(player.display_name))

                if len(room_match.players) >= room_match.size:
                    role = player.guild.get_role(room_match.role_id)
                    await ctx.send("Hey {}! {} players have joined.".format(role.mention, len(room_match.players)))
                    return
            else:
                return await ctx.send("There was an error joining.")
        else:
            return await ctx.send("That room does not exist.")
    else:
        return await ctx.send("Sorry, no rooms exist yet.")


@bot.command(aliases=['x', 'exit', 'disband'])
async def leave(ctx):
    """Leave a room. If you are the host, the room will be disbanded."""
    player = ctx.message.author
    rooms_data = rooms.find(guild=ctx.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if r.host == player.id:
                r.update_active()
                role = player.guild.get_role(r.role_id)
                await r.disband(player.guild)
                try:
                    await ctx.send("The room has been disbanded.")
                except discord.errors.NotFound as e:
                    log(e)
                    
                return
            elif player.id in r.players:
                r.update_active()
                await r.remove_player(player)
                await ctx.send("You have left " + r.activity)
                if len(r.players) < 1:
                    await r.disband(player.guild)
                    return await ctx.send("There are no players left in the room. Room has been disbanded.")
    return await ctx.send("You are not in a room.")


@bot.command(aliases=['k'])
async def kick(ctx):
    """[Host] Kick a player."""
    if not ctx.message.mentions:
        return await ctx.send("Please @mention the kickee.")
    player = ctx.message.author
    kickee = ctx.message.mentions[0]
    if player.id == kickee.id:
        return await ctx.send("You cannot be the kicker and kickee.")

    rooms_data = rooms.find(guild=ctx.message.guild.id, host=player.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if r.host == player.id:
                r.update_active()
                await r.remove_player(kickee)
                await ctx.send("{} has been kicked from {}.".format(kickee.name, r.activity))
                if len(r.players) < 1:
                    await r.disband(player.guild)
                    return await ctx.send("There are no players left in the room. Room has been disbanded.")
                return
    return await ctx.send("You are not the host of a room.")


@bot.command(aliases=['rooms', 'list', 'dir'])
async def ls(ctx):
    """List rooms in current guild."""
    rooms_data = rooms.find(guild=ctx.guild.id)
    embed = discord.Embed(color=discord_blue, title="Rooms")
    exists = False

    for room_data in rooms_data:
        exists = True
        room = Room.from_query(room_data)

        description = room.description if room.description else 'Players: ' + ', '.join(room.players)
        embed.add_field(
            name="{0} ({1}/{2})".format(room.activity, len(room.players), room.size),
            value=description )
    if exists:
        await ctx.send(embed=embed)
    else:
        await ctx.send("No rooms exist yet.")


@bot.command(aliases=['r', 'room'])
async def look(ctx, *args):
    """Shows your current room (or look at another room by activity or player)."""
    rooms_data = rooms.find(guild=ctx.guild.id)
    player_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
    activity_filter = args[0] if args else None

    rooms_data = rooms.find(guild=ctx.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player_filter in r.players or r.activity == activity_filter:
                r.update_active()
                return await ctx.send(embed=r.get_embed(ctx.guild))        
    else:
        return await ctx.send("Sorry, no rooms exist yet.")
    
    return await ctx.send("Could not find room.")


@bot.command(aliases=['e', 'change', 'set'])
async def edit(ctx, *args):
    """[Host] Edit room information. Can set multiple at once using flags (`-activity`, `-description`, `-size`, `-host` value)"""
    r = get_hosted_room(ctx.message.author.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")

    fields = {
        'activity': activity.aliases,
        'description': description.aliases,
        'size': size.aliases,
        'host': host.aliases }

    edits = ' '.join(args).split('-')

    if len(edits) < 2:
        return await ctx.send("Please specify the field(s) using flags (`-activity`, `-description`, `-size`, `-host`).")
    del edits[0] # First index contains useless args before a flag

    for edit in edits:
        words = edit.strip().split(' ')
        valid = False
        f = words[0]
        for field, aliases in fields.items():
            if f == field or f in aliases:
                f_args = tuple(words[1:])
                if field == 'activity':
                    await activity.callback(ctx, *f_args)
                elif field == 'description':
                    await description.callback(ctx, *f_args)
                elif field == 'size':
                    await size.callback(ctx, *f_args)
                elif field == 'host':
                    await host.callback(ctx, *f_args)
                valid = True
                break
        if not valid:
            await ctx.send("The field `{}` is not recognized.".format(f))


@bot.command(aliases=['a', 'game', 'name'])
async def activity(ctx, *args):
    """[Host] Set the name of your room"""
    r = get_hosted_room(ctx.message.author.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")

    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    channel = ctx.guild.get_channel(r.channel_id)
    (flags, words) = pop_flags(args)
    new_value = " ".join(words)

    await role.edit(name="Room - " + new_value)
    await channel.edit(name=new_value)
    r.activity = new_value
    rooms.update(dict(role_id=r.role_id, activity=new_value), ['role_id'])
    return await ctx.send("Updated activity to {}.".format(new_value))


@bot.command(aliases=['d', 'desc', 'note'])
async def description(ctx, *args):
    """[Host] Set the description of your room"""
    r = get_hosted_room(ctx.message.author.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")
    
    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    (flags, words) = pop_flags(args)
    new_value = " ".join(words)

    r.description = new_value
    rooms.update(dict(role_id=r.role_id, description=new_value), ['role_id'])
    return await ctx.send("Updated description for {}.".format(r.activity))


@bot.command(aliases=['s', 'max', 'players'])
async def size(ctx, *args):
    """[Host] Set the max player size of your room"""
    r = get_hosted_room(ctx.message.author.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")
    
    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    (flags, words) = pop_flags(args)
    new_value = " ".join(words)

    try:
        if len(r.players) >= int(new_value):
            return await ctx.send("There are too many players.")
        r.size = min(abs(int(new_value)), 100) # Max room size is 100
        rooms.update(dict(role_id=r.role_id, size=int(new_value)), ['role_id'])
        return await ctx.send("Updated room size to {}.".format(new_value))
    except ValueError:
        return await ctx.send("The new room size must be an integer.")


@bot.command(aliases=['h', 'bestow', 'leader'])
async def host(ctx, *args):
    """[Host] Change the host of your room"""
    r = get_hosted_room(ctx.message.author.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")
    
    r.update_active()

    if not ctx.message.mentions:
        return await ctx.send("Please @mention the new host.")

    role = ctx.guild.get_role(r.role_id)
    (flags, words) = pop_flags(args)
    new_host = ctx.message.mentions[0]

    for p in r.players:
        if p == new_host.id:
            r.host = new_host.id
            rooms.update(dict(role_id=r.role_id, host=new_host.id), ['role_id'])
            return await ctx.send("{} is now the new host of {}.".format(new_host.mention, r.activity))
        return await ctx.send("{} is not in {}.".format(new_host.mention, r.activity))


@bot.command(aliases=['clear', 'delete'])
async def purge(ctx, *args):
    """[ADMIN] Delete room(s) in this server (`-a` for all active rooms, `-b` for all broken rooms). For moderation purposes."""
    player = ctx.message.author
    if not player.guild_permissions.administrator:
        return await ctx.send("You are not an administrator.")

    (flags, words) = pop_flags(args)
    if 'a' not in flags and 'b' not in flags:
        return await ctx.send("Please specify a room (by `@role` or `#channel`) or a flag (`-a`, `-b`).")

    if 'b' in flags:
        deleted_channels = 0
        deleted_roles = 0
        category = discord.utils.get(player.guild.categories, name='Rooms')
        for channel in category.channels:
            if iter_len(rooms.find(guild=ctx.guild.id, channel_id=channel.id)) < 1:
                await channel.delete()
                deleted_channels += 1
        for role in ctx.guild.roles:
            if iter_len(rooms.find(guild=ctx.guild.id, role_id=role.id)) < 1 and role.name.startswith("Room -"):
                await role.delete()
                deleted_roles += 1
        try:
            await ctx.send("{} broken channels and {} broken roles have been deleted.".format(deleted_channels, deleted_roles))
        except discord.errors.NotFound as e:
            log(e)

    if 'a' in flags:
        rooms_data = rooms.find(guild=ctx.guild.id)
        if iter_len(rooms_data) < 1:
            await ctx.send("There are no rooms to delete.")
            if 'a' not in flags:
                await ctx.send("(To delete broken rooms, use `-b`.)")
            return
        count = 0
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            guild = bot.get_guild(r.guild)
            await r.disband(guild)
            count += 1
        try:
            await ctx.send("{} rooms have been deleted.".format(count))
        except discord.errors.NotFound as e:
            log(e)


@bot.command(aliases=['hello'])
async def hi(ctx):
    """It's nice to just say hi sometimes."""
    name = ctx.message.author.name
    greetings = [
        "Hey, hope you're doing well today",
        "Sup {}".format(name),
        "Hi! Tell me to do something, I'm bored",
        "Ay, is there anything you want to do?",
        "Hello world! and also {}!".format(name),
        ":wave:"
    ]
    return await ctx.send(choice(greetings))
    

@bot.command(aliases=['pong'])
async def ping(ctx):
    """Pong! Shows latency."""
    return await ctx.send('Pong! Latency: `{}`'.format(round(bot.latency, 1)))


@bot.command(aliases=['info'])
async def about(ctx):
    """All about me!"""
    embed = discord.Embed(
        color=discord_blue,
        description='\n'.join([
            ":shield: Serving {} servers".format(len(bot.guilds)),
            ":cat: [GitHub](https://github.com/Milotrince/discord-roombot) Help improve me!",
            ":mailbox: [Invite Link](https://discordapp.com/oauth2/authorize?client_id=592816310656696341&permissions=268437520&scope=bot) Invite me to another server!",
            ":woman: [Profile](https://github.com/Milotrince) Contact my creator",
            ":heart: RoomBot was made for Discord Hack Week"]) )
    embed.set_author(name="About RoomBot")
    return await ctx.send(embed=embed)


@bot.command(aliases=['commands'])
async def help(ctx):
    """Shows the available commands."""
    embed = discord.Embed(
        color=discord_blue,
        title="Commands" )
    for command in sorted(bot.commands, key=lambda c:c.name):
        embed.add_field(
            name="**{}**    aka `{}`".format(command, "`, `".join(command.aliases)),
            value=command.short_doc,
            inline=False )
    await ctx.send(embed=embed)


# Disable for full stack trace
@bot.event
async def on_command_error(ctx, error):
    """Sends a message when command error is encountered."""
    log(error)

    if type(error) == discord.ext.commands.errors.CommandNotFound:
        return await ctx.send("Not a valid command. Try `{0}help`.".format(config['prefix']))
    elif type(error) == discord.ext.commands.errors.CommandInvokeError:
        missing_permissions = []
        if not ctx.guild.me.guild_permissions.manage_channels:
            missing_permissions.append("ManageChannels")
        if not ctx.guild.me.guild_permissions.manage_roles:
            missing_permissions.append("ManageRoles")

        if missing_permissions:
            return await ctx.send("It seems I am missing permissions: `{}`".format('`, `'.join(missing_permissions)))
    await ctx.send("Something went wrong. The developer has been notified.")


# Periodically check for inactive rooms
async def delete_inactive_rooms():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(5 ) # check every 5 minutes
        for room_data in rooms.find():
            r = Room.from_query(room_data)
            time_diff = datetime.now(pytz.utc) - r.last_active.replace(tzinfo=pytz.utc)
            # timeout is in minutes
            if time_diff.total_seconds() / 60 >= r.timeout:
                guild = bot.get_guild(r.guild)
                channel = guild.get_channel(r.birth_channel)
                await r.disband(guild)
                await channel.send("{} has disbanded due to inactivity.".format(r.activity))


bot.loop.create_task(delete_inactive_rooms())
bot.run(config['token'])