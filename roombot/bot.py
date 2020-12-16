
from discord.ext import commands, tasks
from roombot.database.settings import Settings
from roombot.database.room import Room
from roombot.utils.pagesembed import PagesEmbed, EmbedPagesEmbed, FieldPagesEmbed
from roombot.utils.roomembed import RoomEmbed
from roombot.utils.functions import now, has_common_element
import discord
import logging
import os

# logging
if os.getenv('ENV') == 'development':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

def log(content):
    print('{} {}'.format(now(), content))

async def logc(content):
    log(content)
    channel_id = os.getenv('LOGGING_CHANNEL_ID')
    guild_id = os.getenv('LOGGING_SERVER_ID')
    if bot and channel_id and guild_id:
        guild = bot.get_guild(int(guild_id))
        if guild:
            channel = guild.get_channel(int(channel_id))
            if channel:
                await channel.send(content)


async def determine_prefix(bot, message):
    guild = message.guild
    if guild:
        settings = Settings.get_for(guild.id)
        if settings and settings.prefix:
            return settings.prefix 
    return Settings.get_default_value('prefix')

# Define bot
intents = discord.Intents.default()
intents.members = True
intents.typing = False
bot = commands.Bot(
    intents=intents,
    command_prefix=determine_prefix, 
    case_insensitive=True,
    activity=discord.Game('the waiting game'))
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
    log('{} is online!'.format(bot.user.name))

@bot.event
async def on_disconnect():
    log('{} has disconnected...'.format(bot.user.name))

@bot.event
async def on_command(ctx):
    settings = Settings.get_for(ctx.guild.id)
    if settings.delete_command_message:
        try:
            await ctx.message.delete()
        except Exception as e:
            log(e)

@bot.event
async def on_voice_state_update(member, before, after):
    s = Settings.get_for(member.guild.id)
    joined = not before.channel and after.channel
    left = before.channel and not after.channel
    try:
        if joined:
            if after.channel.id == s.creation_channel:
                await member.move_to(None)
                await Room.create(member)
            elif after.channel.id == s.voice_creation_channel:
                voice_channel = await member.guild.create_voice_channel(
                    name='\u231b '+member.display_name,
                    bitrate=s.bitrate * 1000,
                    category=after.channel.category,
                    position=0
                )
                await member.move_to(voice_channel)
        elif left and len(before.channel.members) < 1 and before.channel.name.startswith('\u231b'):
            await before.channel.delete()
    except:
        # likely permissions error
        pass

@bot.event
async def on_reaction_add(reaction, user):
    if user.id != bot.user.id:
        await PagesEmbed.on_reaction_add(reaction, user)


@bot.command(pass_context=True)
async def reload(ctx):
    if (str(ctx.message.author.id) == os.getenv('BOT_OWNER_USER_ID')):
        log('reload cogs')
        for cog_name in cogs:
            bot.reload_extension('cogs.' + cog_name)

# Disable for full stack trace
@bot.event
async def on_command_error(ctx, error):
    settings = Settings.get_for(ctx.guild.id)

    if not passes_role_restriction(ctx):
        return
    elif type(error) == commands.errors.MissingPermissions:
        return await ctx.send(settings.get_text('not_admin'))
    elif type(error) == discord.Forbidden:
        await logc("===== FORBIDDEN Error raised from: " + ctx.message.content)
        await logc(error.text)
        return await ctx.send(settings.get_text('not_admin'))
        # return await ctx.send(settings.get_text('missing_permission').format('`, `'.join(missing_permissions)))
    elif type(error) == commands.NoPrivateMessage:
        return
    elif type(error) == commands.errors.CheckFailure:
        return
    elif type(error) == commands.errors.CommandNotFound:
        if settings.respond_to_invalid:
            await ctx.send(settings.get_text('invalid_command').format(ctx.message.content, settings.prefix))
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
            return await ctx.send(settings.get_text('missing_permission').format('`, `'.join(missing_permissions)))
    await logc("===== Error raised from: " + ctx.message.content)
    await logc(error)

    errorText = ''
    try:
        errorText = '```' + str(error) + '```'
    except:
        pass
    finally:
        await ctx.send(errorText + settings.get_text('fatal_error').format(
            settings.prefix + settings.get_text('_commands')['support']['_name']) )



@tasks.loop(seconds=60)
async def delete_inactive():
    try:
        await FieldPagesEmbed.delete_old()
        await EmbedPagesEmbed.delete_old()
        await RoomEmbed.delete_old()
        await Room.delete_inactive(bot)
    except Exception as e:
        await logc("===== Error raised from: delete_inactive")
        await logc(e)

# add cogs (groups of commands)
cogs = [ 'general', 'basicroom', 'roomhost', 'admin' ]
for cog_name in cogs:
    bot.load_extension('roombot.cogs.' + cog_name)


def run_bot():
    delete_inactive.start()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))