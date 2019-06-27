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
bot = commands.Bot(command_prefix=config['prefix'])
bot.remove_command('help')

@bot.event
async def on_ready():
    """Fired when bot comes online"""
    print('{0} is online!'.format(bot.user.name))


@bot.command()
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
            if player.name in r.players:
                return await ctx.send("You are already in a room.")
            if r.activity == activity:
                activity += " ({})".format(player.name)

    role = await player.guild.create_role(
        name="Room - " + activity,
        color=discord.Color.blue(),
        hoist=True,
        mentionable=True )
    new_room = Room.from_message(activity, ctx, args, role.id)
    await new_room.add_player(player)
    emb = new_room.get_embed()
    await ctx.send(embed=emb)


@bot.command()
async def join(ctx, *args):
    """Join a room (by activity or player)."""
    # TODO: If full, send ping
    if len(args) < 1:
        return await ctx.send("Please specify a room by activity or player.")
    filter = " ".join(args)

    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        room_match = None
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if ctx.message.author.name in r.players:
                return await ctx.send("You are already in a room.")
            elif r.activity == filter or filter in room.players:
                room_match = r
                
        if room_match:
            player = ctx.message.author
            if await room_match.add_player(player):
                await ctx.send(embed=room_match.get_embed())
            else:
                await ctx.send("There was an error joining.")
    else:
        await ctx.send("Sorry, no rooms exist yet.")


@bot.command()
async def leave(ctx):
    """Leave a room."""
    player = ctx.message.author
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if player.name in r.players:
                await r.remove_player(player)
                return await ctx.send("You have left " + r.activity)
    else:
        return ctx.send("You are not in a room.")


@bot.command()
async def list(ctx):
    """List rooms in current guild."""
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    embed = discord.Embed(color=discord.Color.blue(), title="Rooms")
    exists = False

    for room_data in rooms_data:
        exists = True
        room = Room.from_query(room_data)

        description = room.description if room.description else 'Players: ' + ', '.join(room.players)
        embed.add_field(
            name="{0} ({1}/{2})".format(room.activity, len(room.players), room.waiting_for),
            value=description )
    if exists:
        await ctx.send(embed=embed)
    else:
        await ctx.send("No rooms exist yet.")


@bot.command()
async def room(ctx, *args):
    """Shows your current room (or look at another room by activity or player)."""
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    filter = args[0] if args else ctx.message.author.name

    rooms_data = rooms.find(guild=ctx.message.guild.id)
    if rooms_data:
        for room_data in rooms_data:
            r = Room.from_query(room_data)
            if filter in r.players or r.activity == filter:
                return await ctx.send(embed=r.get_embed())        
    else:
        return await ctx.send("Sorry, no rooms exist yet.")
    
    return await ctx.send("Could not find room.")


@bot.command()
async def ping(ctx):
    """Pong! Shows latency."""
    await ctx.send('Pong! Latency: `{0}`'.format(round(bot.latency, 1)))


@bot.command()
async def help(ctx):
    """Shows the available commands."""
    embed = discord.Embed(
        color=discord.Color.blue(),
        title="Commands" )
    for command in bot.commands:
        embed.add_field(
            name=command,
            value=command.short_doc )
    await ctx.send(embed=embed)


# Disable for full stack trace
@bot.event
async def on_command_error(ctx, error):
    """Sends an error message when error is encountered."""
    pprint(error)

    if type(error) == discord.ext.commands.errors.CommandNotFound:
        await ctx.send("Not a valid command. Try `{0}help`.".format(config['prefix']))
    else:
        await ctx.send("An error has occurred.")


bot.run(config['token'])