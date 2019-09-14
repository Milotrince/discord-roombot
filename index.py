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


# Define bot
bot = commands.Bot(command_prefix=config['prefix'], case_insensitive=True)
bot.remove_command('help')
discord_blue = discord.Color.from_rgb(114, 137, 218)
invitee_list = []


@bot.event
async def on_ready():
    """Fired when bot comes online"""
    print('{} is online!'.format(bot.user.name))
    await bot.change_presence(activity=discord.Game(name='the waiting game'))

@bot.event
async def on_disconnect():
    """Fired when bot goes offline"""
    print('{} has disconnected...'.format(bot.user.name))

@bot.event
async def on_command(ctx):
    if config["delete_command_message"] == "true":
        await ctx.message.delete()


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
    # await role.edit(position=1)
    existing_category = discord.utils.get(player.guild.categories, name='Rooms')
    category = existing_category if existing_category else await player.guild.create_category('Rooms')
    channel = await player.guild.create_text_channel(activity, category=category, position=0, overwrites={
        player.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        player.guild.me: discord.PermissionOverwrite(read_messages=True),
        role: discord.PermissionOverwrite(read_messages=True) })

    new_room = Room.from_message(activity, ctx, args, role.id, channel.id, role.color)
    new_room.update_active()
    success = await new_room.add_player(player)
    if success:
        emb = new_room.get_embed(player, "New room made")
        await channel.send(create_message(player.display_name))
        return await ctx.send(embed=emb)
    return await ctx.send("There was an error creating the room. Please try again.")


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
                await ctx.send(embed=room_match.get_embed(player, "Room joined by"))
                room_channel = ctx.guild.get_channel(room_match.channel_id)
                await room_channel.send(join_message(player.display_name))

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


@bot.command(aliases=['i'])
async def invite(ctx, *args):
    """Invite a player/players to your room (by name or mention)."""
    if len(args) < 1:
        return await ctx.send("Please specify the name or mention of the invitee.")
    user_mentions = ctx.message.mentions
    role_mentions = ctx.message.role_mentions
    player = ctx.message.author
    invitees = []
    room = None
    
    for invitee in user_mentions:
        if invitee.id not in invitees:
            invitees.append(invitee.id)

    for role in role_mentions:
        for member in role.members:
            if member.id not in invitees:
                invitees.append(member.id)

    player_names = []
    for member in ctx.guild.members:
        player_names.append(member.display_name.lower())
        player_names.append(member.name.lower())

    for arg in args:
        if arg in player_names:
            p = discord.utils.find(lambda p: p.name.lower() == arg.lower(), ctx.guild.members)
            if p and p.id not in invitees:
                invitees.append(p.id)

    rooms_data = rooms.find(guild=ctx.guild.id)
    room_match = None
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player.id in r.players:
                room = r
    if not room:
        return await ctx.send("You are not in a room.")

    if not invitees:
        return await ctx.send("Invite who? (Check if the username is correct?)")
                
    room.update_active()
    embed = discord.Embed(
        color=discord_blue,
        description="Lucky you.",
        timestamp=datetime.now(pytz.utc),
        title=invite_message(player.display_name, room.activity) )
    embed.add_field(
        name="Players ({}/{})".format(len(room.players), room.size),
        value="<@{}>".format(">, <@".join([str(id) for id in room.players])) )
    embed.add_field(
        name="Inviter: " + player.display_name,
        value="Server: " + player.guild.name )
    embed.add_field(
        name="Room: " + room.activity,
        value="Note: " + room.description )
    embed.add_field(
        name="Room ID",
        value=room.role_id )
    embed.set_footer(
        text="React to accept or decline the invite.",
        icon_url=discord.Embed.Empty )


    result_embed = discord.Embed(
        color=discord_blue,
        description="for room: `{}`".format(room.activity),
        timestamp=datetime.now(pytz.utc),
        title="Invites Sent" )
    result_embed.set_footer(
        text="Invites sent by: " + player.display_name,
        icon_url=discord.Embed.Empty )
    invitee_success = []
    invitee_fail = []
    invitee_already_joined = []
    for invitee_id in invitees:
        try:
            if invitee_id in room.players:
                invitee_already_joined.append(invitee_id)
                continue
            invitee = bot.get_user(invitee_id)
            m = await invitee.send(embed=embed)
            await m.add_reaction('✅')
            await m.add_reaction('❌')
            invitee_list.append(invitee_id)
            invitee_success.append(invitee_id)
        except discord.errors.Forbidden as e:
            invitee_fail.append(invitee_id)

    if invitee_success:
        result_embed.add_field(
            name="Invitees",
            value="<@{}>".format(">, <@".join([str(id) for id in invitee_success])) )
    if invitee_fail:
        result_embed.add_field(
            name="Failed invites",
            value="I was unable to access these folks, probably because of their settings or because they are a bot.\n<@{}>".format(">, <@".join([str(id) for id in invitee_fail])) )
    if invitee_already_joined:
        result_embed.add_field(
            name="Already joined",
            value="<@{}>".format(">, <@".join([str(id) for id in invitee_already_joined])) )
        
    return await ctx.send(embed=result_embed)

    
@bot.event
async def on_reaction_add(reaction, user):
    player = user
    channel = reaction.message.channel
    accept = reaction.emoji == '✅'
    decline = reaction.emoji == '❌'
    valid_invite_emoji = accept or decline
    from_dm = type(channel) is discord.channel.DMChannel
    if not valid_invite_emoji or player.id not in invitee_list or not from_dm:
        return

    invitee_list.remove(player.id)
    room_id = None
    for field in reaction.message.embeds[0].fields:
        if field.name == "Room ID":
            room_id = field.value
            break
    room = None
    room_data = rooms.find_one(role_id=room_id)
    if room_data:
        room = Room.from_query(room_data)
    if not room:
        return await channel.send("Room no longer exists.")

    if (accept):
        if player.id in room.players:
            return await channel.send("You are already in that room.")
        await channel.send("Invite accepted.")
        room.update_active()
        guild = bot.get_guild(room.guild)
        player = guild.get_member(player.id)
        if not guild:
            return await channel.send("I am not in that server anymore :(")
        if await room.add_player(player):
            await channel.send(embed=room.get_embed(player, "Room joined by"))
            room_channel = guild.get_channel(room.channel_id)
            await room_channel.send(join_message(player.display_name))

            if len(room.players) >= room.size:
                role = guild.get_role(room.role_id)
                room_channel = guild.get_channel(room.channel_id)
                await room_channel.send("Hey {}! {} players have joined.".format(role.mention, len(room.players)))
    else:
        await channel.send("Invite declined.")
            


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
                    await ctx.send("{}'s room `{}` has been disbanded.".format(player.display_name, r.activity))
                except discord.errors.NotFound as e:
                    log(e)
                    
                return
            elif player.id in r.players:
                r.update_active()
                await r.remove_player(player)
                await ctx.send("{} has left `{}`".format(player.name, r.activity))
                if len(r.players) < 1:
                    await r.disband(player.guild)
                    return await ctx.send("There are no players left in the room. Room has been disbanded.")
                return
    return await ctx.send("{}, you cannot leave a room if you are not in one.".format(player.display_name))


@bot.command(aliases=['k'])
async def kick(ctx):
    """**[Host]** Kick a player."""
    if not ctx.message.mentions:
        return await ctx.send("Please @mention the kickee.")
    player = ctx.message.author
    kickee = ctx.message.mentions[0]
    if player.id == kickee.id:
        return await ctx.send("{}, why are you trying to kick yourself?".format(player.display_name))

    rooms_data = rooms.find(guild=ctx.message.guild.id, host=player.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if r.host == player.id:
                r.update_active()
                await r.remove_player(kickee)
                await ctx.send("{} has kicked {} from {}.".format(player.display_name, kickee.display_name, r.activity))
                if len(r.players) < 1:
                    await r.disband(player.guild)
                    return await ctx.send("There are no players left in the room. Room has been disbanded.")
                return
    return await ctx.send("{}, you are not the host of a room.".format(player.display_name))


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
    player_name = ctx.message.author.display_name
    rooms_data = rooms.find(guild=ctx.guild.id)
    player_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
    activity_filter = " ".join(args) if args else None
    role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

    rooms_data = rooms.find(guild=ctx.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player_filter in r.players or r.activity == activity_filter or r.role_id == role_mention_filter:
                r.update_active()
                return await ctx.send(embed=r.get_embed(ctx.author, "Request")) 
    else:
        return await ctx.send("Oh {}, looks like no rooms exist yet.".format(player_name))
    
    return await ctx.send("Sorry {}, I could not find your room.".format(player_name))


@bot.command(aliases=['e', 'change', 'set'])
async def edit(ctx, *args):
    """**[Host]** Edit room information. Can set multiple at once using flags (`-activity`, `-description`, `-size`, `-host` value)"""
    player = ctx.message.author
    r = get_hosted_room(player.id, ctx.guild.id)
    if not r:
        return await ctx.send("{}, you are not the host of a room.".format(player.display_name))

    fields = {
        'activity': activity.aliases,
        'description': description.aliases,
        'size': size.aliases,
        'host': host.aliases,
        'color': color.aliases }

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
                elif field == 'color':
                    await color.callback(ctx, *f_args)
                valid = True
                break
        if not valid:
            await ctx.send("The field `{}` is not recognized.".format(f))


@bot.command(aliases=['a', 'game', 'name'])
async def activity(ctx, *args):
    """**[Host]** Set the name of your room"""
    player = ctx.message.author
    r = get_hosted_room(player.id, ctx.guild.id)
    if not r:
        return await ctx.send("{}, you are not the host of a room.".format(player.display_name))

    channel = ctx.guild.get_channel(r.channel_id)

    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    channel = ctx.guild.get_channel(r.channel_id)
    (flags, words) = pop_flags(args)
    new_value = " ".join(words)

    await role.edit(name="Room - " + new_value)
    await channel.edit(name=new_value)
    r.activity = new_value
    rooms.update(dict(role_id=r.role_id, activity=new_value), ['role_id'])
    return await ctx.send("{} updated activity for {}.".format(player.display_name, channel.mention))


@bot.command(aliases=['d', 'desc', 'note'])
async def description(ctx, *args):
    """**[Host]** Set the description of your room"""
    player = ctx.message.author
    r = get_hosted_room(player.id, ctx.guild.id)
    if not r:
        return await ctx.send("{}, you are not the host of a room.".format(player.display_name))
    
    channel = ctx.guild.get_channel(r.channel_id)

    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    (flags, words) = pop_flags(args)
    new_value = " ".join(words)

    r.description = new_value
    rooms.update(dict(role_id=r.role_id, description=new_value), ['role_id'])
    await channel.edit(topic="({}/{}) {}".format(len(r.players), r.size, r.description))
    
    return await ctx.send("{} updated the description for {}.".format(player.display_name, channel.mention))


@bot.command(aliases=['s', 'max', 'players'])
async def size(ctx, *args):
    """**[Host]** Set the max player size of your room"""
    player = ctx.message.author
    r = get_hosted_room(player.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")
    
    channel = ctx.guild.get_channel(r.channel_id)
    
    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    (flags, words) = pop_flags(args)
    new_value = " ".join(words)

    try:
        if len(r.players) > int(new_value):
            return await ctx.send("There are too many players.")
        elif len(r.players) == int(new_value):
            await ctx.send("The room is now full.")
        r.size = min(abs(int(new_value)), 100) # Max room size is 100
        rooms.update(dict(role_id=r.role_id, size=int(new_value)), ['role_id'])
        return await ctx.send("{} updated room size of {} to {}.".format(player.display_name, channel.mention, new_value))
    except ValueError:
        return await ctx.send("The new room size must be an integer.")


@bot.command(aliases=['h', 'bestow', 'leader'])
async def host(ctx, *args):
    """**[Host]** Change the host of your room"""
    player = ctx.message.author
    r = get_hosted_room(player.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")
    
    r.update_active()
    new_host = ctx.message.mentions[0] if ctx.message.mentions else None

    name_filter = " ".join(args)
    for id in r.players:
        p = ctx.guild.get_member(id)
        if p.display_name == name_filter:
            new_host = p

    if not new_host:
        return await ctx.send("Please @mention or type the name of the new host.")

    channel = ctx.guild.get_channel(r.channel_id)

    role = ctx.guild.get_role(r.role_id)
    (flags, words) = pop_flags(args)

    for p in r.players:
        if p == new_host.id:
            r.host = new_host.id
            rooms.update(dict(role_id=r.role_id, host=new_host.id), ['role_id'])
            return await ctx.send("{} is now the new host of {}.".format(new_host.mention, channel.mention))
    return await ctx.send("{} is not in {}.".format(new_host.mention, channel.mention))


@bot.command(aliases=['c', 'colour'])
async def color(ctx, *args):
    """**[Host]** Set the color of your room"""
    player = ctx.message.author
    r = get_hosted_room(player.id, ctx.guild.id)
    if not r:
        return await ctx.send("You are not the host of a room.")

    channel = ctx.guild.get_channel(r.channel_id)

    r.update_active()
    role = ctx.guild.get_role(r.role_id)
    channel = ctx.guild.get_channel(r.channel_id)
    
    color = get_color(" ".join(args))

    await role.edit(color=color)
    rooms.update(dict(role_id=r.role_id, color=color.value), ['role_id'])
    return await ctx.send("{} updated color for {}.".format(player.display_name, channel.mention))


@bot.command(aliases=['clear', 'delete'])
async def purge(ctx, *args):
    """**[ADMIN]** Delete room(s) in this server (`-a` for all active rooms, `-b` for all broken rooms). For moderation purposes."""
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
            ":woman: [GitHub Profile](https://github.com/Milotrince) Contact my creator @Milotrince#0001",
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
        if config["respond_to_invalid_command"] == "true":
            await ctx.send("\"{}\" is not a valid command. Try `{}help`.".format(ctx.message.content, config['prefix']))
        if config["delete_command_message"] == "true":
            await ctx.message.delete()
        return
    elif type(error) == discord.ext.commands.errors.CommandInvokeError:
        missing_permissions = []
        if not ctx.guild.me.guild_permissions.manage_channels:
            missing_permissions.append("ManageChannels")
        if not ctx.guild.me.guild_permissions.manage_roles:
            missing_permissions.append("ManageRoles")
        if not ctx.guild.me.guild_permissions.manage_messages:
            missing_permissions.append("ManageMessages")

        if missing_permissions:
            return await ctx.send("It seems I am missing permissions: `{}`".format('`, `'.join(missing_permissions)))
    await ctx.send("Something went wrong. If this keeps happening, please post an issue at GitHub (https://github.com/Milotrince/discord-roombot/issues)")


# Periodically check for inactive rooms
async def delete_inactive_rooms():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(5 * 60) # check every 5 minutes
        for room_data in rooms.find():
            r = Room.from_query(room_data)
            time_diff = datetime.now(pytz.utc) - r.last_active.replace(tzinfo=pytz.utc)
            # timeout is in minutes
            if time_diff.total_seconds() / 60 >= r.timeout:
                try:
                    guild = bot.get_guild(r.guild)
                    channel = guild.get_channel(r.birth_channel) if guild else None
                    if guild and channel:
                        await r.disband(guild)
                        await channel.send("{} has disbanded due to inactivity.".format(r.activity))
                    else:
                        rooms.delete(role_id=r.role_id)

                except Exception as e:
                    log(e)


bot.loop.create_task(delete_inactive_rooms())
bot.run(config['token'])
