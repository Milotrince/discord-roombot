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
    activities = ctx.message.author.activities
    if not args:
        for a in activities:
            activity = a.name
            break
    else:
        activity = " ".join(args)
    
    if not activity:
        return await ctx.send('Please specify the room activity (or start doing something).')

    new_room = Room.from_message(activity, ctx, args)
    emb = new_room.get_embed()
    await ctx.send(embed=emb)


@bot.command()
async def join(ctx, *args):
    """Join a room (by activity or player)."""

    if len(args) < 1:
        return await ctx.send("Please specify a room by activity or player.")
    filter = args[0]

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
            member = ctx.message.author
            if room_match.add_player(member.name):
                role = await member.guild.create_role(name=room_match.activity)
                print(role)
                await member.add_roles(role)
                await ctx.send(embed=room_match.get_embed())
            else:
                await ctx.send("There was an error joining.")
    else:
        await ctx.send("Sorry, no rooms exist yet.")
        

@bot.command()
async def list(ctx):
    """List rooms in current guild."""
    rooms_data = rooms.find(guild=ctx.message.guild.id)
    exists = False

    embed = discord.Embed(color=discord.Color.blue())
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


@bot.event
async def on_command_error(ctx, error):
    pprint(error)

    if type(error) == discord.ext.commands.errors.CommandNotFound:
        await ctx.send("Not a valid command. Try `{0}help`.".format(config['prefix']))
    else:
        await ctx.send("An error has occurred.")


bot.run(config['token'])