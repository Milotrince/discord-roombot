from discord.ext import commands
from room import *

print("""
._____               _____._____._____.
| __  |___ ___ ____.| __  |     |_   _|
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
bot = commands.Bot(
    command_prefix=determine_prefix, 
    case_insensitive=True,
    activity=discord.Game(strings['bot_presence']))
bot.remove_command('help')

@bot.check
def passes_role_restriction(ctx):
    member = ctx.message.author
    settings = Settings.get_for(ctx.guild.id)
    if len(settings.role_restriction) > 0:
        role_ids = [ role.id for role in member.roles ]
        return has_common_element(role_ids, settings.role_restriction) or member.guild_permissions.administrator
    return True

@bot.event
async def on_ready():
    print('{} is online!'.format(bot.user.name))

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

    if not passes_role_restriction(ctx):
        return
    elif type(error) == commands.errors.MissingPermissions:
        return await ctx.send(strings['not_admin'])
    elif type(error) == commands.errors.CheckFailure:
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
    log("===== ERROR RAISED FROM: " + ctx.message.content)
    log(error)
    await ctx.send(strings['fatal_error'])


# Periodically check for inactive rooms
async def delete_inactive_rooms_db():
    await bot.wait_until_ready()
    try:
        while not bot.is_closed():
            await asyncio.sleep(60) # check every minute
            for room_data in rooms_db.find():
                r = Room.from_query(room_data)
                if r.timeout and r.timeout >= 1:
                    guild = bot.get_guild(r.guild)
                    birth_channel = guild.get_channel(r.birth_channel) if guild else None
                    channel = guild.get_channel(r.channel_id) if guild else None

                    if (channel):
                        last_message = (await channel.history(limit=1).flatten())[0]
                        last_message_datetime = last_message.created_at.replace(tzinfo=pytz.utc)
                        voice_channel = guild.get_channel(r.voice_channel_id) if guild else None
                        if voice_channel and len(voice_channel.members) > 0:
                            r.update_active()
                        if last_message_datetime > r.last_active.replace(tzinfo=pytz.utc):
                            r.update('last_active', last_message_datetime)

                    time_diff = datetime.now(pytz.utc) - r.last_active.replace(tzinfo=pytz.utc)

                    # timeout is in minutes
                    if time_diff.total_seconds() / 60 >= r.timeout:
                        try:
                            if guild:
                                await r.disband(guild)
                                if birth_channel:
                                    await birth_channel.send(strings['disband_from_inactivity'].format(r.activity))
                            else:
                                rooms_db.delete(role_id=r.role_id)
                        except Exception as e:
                            log(e)
    except Exception as e:
        log(e)
        log("Restarting delete inactive rooms task")
        bot.loop.create_task(delete_inactive_rooms_db())


bot.loop.create_task(delete_inactive_rooms_db())

# init strings for settings
Settings.set_strings();

# add cogs (groups of commands)
cogs_folder = 'cogs'
cogs = [ 'generic', 'basicroom', 'roomhost', 'admin' ]
for cog_name in cogs:
    bot.load_extension(cogs_folder + '.' + cog_name)
for cog in bot.cogs.values():
    for command in cog.get_commands():
        command.name = strings['_name'][command.name]
        command.help = '\n'.join(strings['_help'][command.name])
        # command.aliases = strings['_aliases'][command.name]

# run bot
with open('config/token.txt', 'r') as token_file:  
    token = token_file.read()
bot.run(token)
