import os
import json
import dataset
import discord
from discord.ext import commands
from datetime import datetime

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
    
# Start database
db = dataset.connect('sqlite:///:memory:')
rooms = db['rooms']

# Define bot
bot = commands.Bot(command_prefix=config['prefix'])

@bot.event
async def on_ready():
    print('{0} is online!'.format(bot.user.name))


@bot.command()
async def new(ctx):
    """Make new room"""
    new_room = dict(
        guild=ctx.message.guild,
        activity="activity",
        description="",
        created=datetime.now(),
        timeout=config['timeout'],
        players=[ctx.message.author],
        waiting_for=2
    )
    rooms.insert(new_room)
    emb = room_embed(new_room)
    await ctx.send(embed=emb)

@bot.command()
async def ping(ctx):
    """Pong!"""
    await ctx.send("Pong!")

    
def room_embed(info):
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=info.description,
        timestamp=info.created )
    embed.set_author(name=info.activity)
    embed.add_field(
        name="Players ({0})".format(len(info.players)),
        value=", ".join(info.players) )
    embed.add_field(
        name="Waitng for {0} players".format(info.waiting_for),
        value="Room will disband in {0} {1}".format(info.timeout, 'seconds') )
    embed.set_footer(
        text="Host: {0}".format(info.host.name),
        icon_url=info.host.avatars )
        
    return embed

bot.run(config['token'])