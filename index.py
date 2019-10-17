import asyncio
import json
import os
import dataset
from discord.ext import commands
from utility import *
from room import *
from cogs import *


print("""
 _____               _____ _____ _____ 
| __  |___ ___ _____| __  |     |_   _|
|    -| . | . |     | __ -|  |  | | |  
|__|__|___|___|_|_|_|_____|_____| |_|
""")

# Start database
db = dataset.connect('sqlite:///database.db')
rooms = db.get_table('rooms', primary_id='role_id')

# Get config file
current_dir = os.path.dirname(__file__)
with open(os.path.join(current_dir, 'config.json')) as config_file:  
    config = json.load(config_file)
with open(os.path.join(current_dir, 'settings.json')) as settings_file:  
    default_settings = json.load(settings_file)


# Define bot
bot = commands.Bot(command_prefix=config['prefix'], case_insensitive=True)
bot.remove_command('help')

    

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

# Disable for full stack trace
@bot.event
async def on_command_error(ctx, error):
    """Sends a message when command error is encountered."""
    if type(error) == commands.errors.CheckFailure:
        return
    elif type(error) == commands.errors.CommandNotFound:
        if config["respond_to_invalid_command"] == "true":
            await ctx.send("\"{}\" is not a valid command. Try `{}help`.".format(ctx.message.content, config['prefix']))
        if config["delete_command_message"] == "true":
            await ctx.message.delete()
        return
    elif type(error) == commands.errors.CommandInvokeError:
        missing_permissions = []
        if not ctx.guild.me.guild_permissions.manage_channels:
            missing_permissions.append("ManageChannels")
        if not ctx.guild.me.guild_permissions.manage_roles:
            missing_permissions.append("ManageRoles")
        if not ctx.guild.me.guild_permissions.manage_messages:
            missing_permissions.append("ManageMessages")

        if missing_permissions:
            return await ctx.send("It seems I am missing permissions: `{}`".format('`, `'.join(missing_permissions)))
    log(error)
    await ctx.send("Something went wrong. If this keeps happening, please message `Milotrince#0001` or post an issue at GitHub (https://github.com/Milotrince/discord-roombot/issues)")


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

# add cogs (groups of commands)
bot.add_cog(generic.Generic(bot)) 
bot.add_cog(basicroom.BasicRoom(bot))
bot.add_cog(roomhost.RoomHost(bot))
bot.add_cog(admin.Admin(bot))

bot.loop.create_task(delete_inactive_rooms())
bot.run(config['token'])
