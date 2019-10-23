from discord.ext import commands
from room import *
from cogs import *

print("""
 _____               _____ _____ _____ 
| __  |___ ___ _____| __  |     |_   _|
|    -| . | . |     | __ -|  |  | | |  
|__|__|___|___|_|_|_|_____|_____| |_|
""")

async def determine_prefix(bot, message):
    guild = message.guild
    if guild:
        settings = Settings.get_for(guild.id)
        if settings and settings.prefix:
            return settings.prefix 
    return Settings.get_default_value('prefix')

# Define bot
bot = commands.Bot(command_prefix=determine_prefix, case_insensitive=True)
bot.remove_command('help')

@bot.event
async def on_ready():
    print('{} is online!'.format(bot.user.name))
    await bot.change_presence(activity=discord.Game(name=strings['bot_presence']))

@bot.event
async def on_disconnect():
    print('{} has disconnected...'.format(bot.user.name))

@bot.event
async def on_command(ctx):
    settings = Settings.get_for(ctx.guild.id)
    if settings.delete_command_message:
        await ctx.message.delete()

# Disable for full stack trace
@bot.event
async def on_command_error(ctx, error):
    """Sends a message when command error is encountered."""
    settings = Settings.get_for(ctx.guild.id)

    if type(error) == commands.errors.CheckFailure:
        return
    elif type(error) == commands.errors.CommandNotFound:
        if settings.respond_to_invalid:
            await ctx.send(strings['invalid_command'].format(ctx.message.content, settings.prefix))
        if settings.delete_command_message:
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
            return await ctx.send(strings['missing_permission'].format('`, `'.join(missing_permissions)))
    log(error)
    await ctx.send(strings['fatal_error'])


# Periodically check for inactive rooms
async def delete_inactive_rooms_db():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(5 * 60) # check every 5 minutes
        for room_data in rooms_db.find():
            r = Room.from_query(room_data)
            time_diff = datetime.now(pytz.utc) - r.last_active.replace(tzinfo=pytz.utc)
            # timeout is in minutes
            if time_diff.total_seconds() / 60 >= r.timeout:
                try:
                    guild = bot.get_guild(r.guild)
                    channel = guild.get_channel(r.birth_channel) if guild else None
                    if guild and channel:
                        await r.disband(guild)
                        await channel.send(strings['disband_from_inactivity'].format(r.activity))
                    else:
                        rooms_db.delete(role_id=r.role_id)

                except Exception as e:
                    log(e)

# add cogs (groups of commands)
cogs = [
    generic.Generic(bot),
    basicroom.BasicRoom(bot),
    roomhost.RoomHost(bot),
    admin.Admin(bot) ]
for cog in cogs:
    for command in cog.get_commands():
        command.aliases = strings['_aliases'][command.name]
        command.help = '\n'.join(strings['_help'][command.name])
        command.name = strings['_name'][command.name]
    bot.add_cog(cog)


bot.loop.create_task(delete_inactive_rooms_db())

with open('config/token.txt', 'r') as token_file:  
    token = token_file.read()
bot.run(token)
