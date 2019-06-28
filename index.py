import json
import os
from discord.ext import commands
from room import *
from pprint import pprint 

# https://discordapp.com/api/oauth2/authorize?client_id=592816310656696341&permissions=268576768&scope=bot
print("""
 _____               _____ _____ _____ 
| __  |___ ___ _____| __  |     |_   _|
|    -| . | . |     | __ -|  |  | | |  
|__|__|___|___|_|_|_|_____|_____| |_|
""")

# Get config file
current_dir = os.path.dirname(__file__)
with open(os.path.join(current_dir, 'config.json')) as config_file:  
    config = json.load(config_file)

# Define bot
bot = commands.Bot(command_prefix=config['prefix'], case_insensitive=True)
bot.remove_command('help')


@bot.event
async def on_ready():
    """Fired when bot comes online"""
    print('{0} is online!'.format(bot.user.name))


@bot.event
async def on_disconnect():
    """Fired when bot goes offline"""
    print('{0} has disconnected...'.format(bot.user.name))


@bot.command(aliases=['n', 'host', 'create', 'start'])
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

    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player.id in r.players:
                return await ctx.send("You are already in a room.")
            if r.activity == activity:
                activity += " ({})".format(player.name)

    role = await player.guild.create_role(
        name="Room - " + activity,
        color=discord.Color.blue(),
        hoist=True,
        mentionable=True )
    new_room = Room.from_message(activity, ctx, args, role.id)
    success = await new_room.add_player(player)
    if success:
        emb = new_room.get_embed(player.guild)
        return await ctx.send(embed=emb)
    return await ctx.send("There was an error. Please try again.")


@bot.command(aliases=['j'])
async def join(ctx, *args):
    """Join a room (by activity or player)."""
    if len(args) < 1:
        return await ctx.send("Please specify a room by activity or player.")
    player_filter = ctx.message.mentions[0].id if ctx.message.mentions else None
    activity_filter = " ".join(args) if args else None

    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        room_match = None
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if ctx.message.author.name in r.players:
                return await ctx.send("You are already in a room.")
            elif r.activity == activity_filter or player_filter in r.players:
                room_match = r
                
        if room_match:
            player = ctx.message.author
            if await room_match.add_player(player):
                await ctx.send(embed=room_match.get_embed(player.guild))
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
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if r.host == player.id:
                role = player.guild.get_role(r.role_id)
                await r.disband(player.guild)
                return await ctx.send("The room has been disbanded.")
            elif player.id in r.players:
                await r.remove_player(player)
                await ctx.send("You have left " + r.activity)
                if len(r.players) < 1:
                    await r.disband(player.guild)
                    return await ctx.send("There are no players left in the room. Room has been disbanded.")
    return await ctx.send("You are not in a room.")


@bot.command(aliases=['k'])
async def kick(ctx):
    """(Host) Kick a player."""
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
                await r.remove_player(player)
                await ctx.send("You have left " + r.activity)
                if len(r.players) < 1:
                    await r.disband(player.guild)
                    return await ctx.send("There are no players left in the room. Room has been disbanded.")
    return await ctx.send("You are not the host of a room.")


@bot.command(aliases=['rooms', 'list'])
async def ls(ctx):
    """List rooms in current guild."""
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    embed = discord.Embed(color=discord.Color.blue(), title="Rooms")
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
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    player_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
    activity_filter = args[0] if args else None

    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player_filter in r.players or r.activity == activity_filter:
                return await ctx.send(embed=r.get_embed(ctx.guild))        
    else:
        return await ctx.send("Sorry, no rooms exist yet.")
    
    return await ctx.send("Could not find room.")


@bot.command(aliases=['e', 'change', 'set'])
async def edit(ctx, *args):
    """(Host) Set room information. (need a -field)"""
    fields = {
        'activity': ['activity', 'act','a', 'game', 'name', 'n'],
        'description': ['description', 'desc', 'd', 'note'],
        'size': ['size', 's', 'max'],
        'host': ['host', 'h', 'leader', 'owner']
    }
    field = None
    flag = None
    for arg in args:
        if arg.startswith('-'):
            for f, aliases in fields.items():
                if arg[1:] in aliases:
                    if not field:
                        field = f
                        flag = arg
                    else:
                        return await ctx.send("Cannot change multiple fields.")
    if field:
        words = list(args)
        words.remove(flag)
        new_value = " ".join(words)
        player = ctx.message.author
        rooms_data = rooms.find(guild=ctx.message.guild.id)
        if rooms_data:
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                if r.host == player.id:
                    role = player.guild.get_role(r.role_id)

                    if field == 'activity':
                        await role.edit(name=new_value)
                        r.activity = new_value
                        rooms.update(dict(role_id=r.role_id, activity=new_value), ['role_id'])
                        return await ctx.send("Updated activity.")
                    elif field == 'description':
                        r.description = new_value
                        rooms.update(dict(role_id=r.role_id, description=new_value), ['role_id'])
                        return await ctx.send("Updated description.")
                    elif field == 'size':
                        try:
                            if len(r.players) >= int(new_value):
                                return await ctx.send("There are too many players.")
                            r.size = int(new_value)
                            rooms.update(dict(role_id=r.role_id, size=int(new_value)), ['role_id'])
                            return await ctx.send("Updated room size.")
                        except ValueError:
                            return await ctx.send("The value must be a digit.")
                    elif field == 'host':
                        if not ctx.message.mentions:
                            return await ctx.send("Please @mention the kickee.")
                        new_host = ctx.message.mentions[0]
                        for p in r.players:
                            if p == new_host.id:
                                r.host = new_host.id
                                rooms.update(dict(role_id=r.role_id, host=new_host.id), ['role_id'])
                                return await ctx.send("Changed host.")
                            return await ctx.send("{} is not in your room.".format(new_host.mention))
                    else:
                        return await ctx.send("Field not recognized.")
    else:
        fields_text = []
        for f in fields.keys():
            fields_text.append('`-{}({})`'.format(f[0], f[1:]))
        return await ctx.send("Please specify a valid field\n[{}]".format(', '.join(fields_text)))
    return await ctx.send("You are not the host of a room.")


@bot.command(aliases=['pong'])
async def ping(ctx):
    """Pong! Shows latency."""
    await ctx.send('Pong! Latency: `{0}`'.format(round(bot.latency, 1)))


@bot.command(aliases=['commands'])
async def help(ctx):
    """Shows the available commands."""
    embed = discord.Embed(
        color=discord.Color.blue(),
        title="Commands" )
    for command in bot.commands:
        embed.add_field(
            name=command,
            value="`{}`\n{}".format("`, `".join(command.aliases), command.short_doc) )
    await ctx.send(embed=embed)


# Disable for full stack trace
@bot.event
async def on_command_error(ctx, error):
    """Sends a message when command error is encountered."""
    print(error)

    if type(error) == discord.ext.commands.errors.CommandNotFound:
        await ctx.send("Not a valid command. Try `{0}help`.".format(config['prefix']))
    else:
        await ctx.send("An error has occurred.")


bot.run(config['token'])