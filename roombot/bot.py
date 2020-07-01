
from discord.ext import commands, tasks
from roombot.database.settings import *
from roombot.database.room import *
from roombot.utils.pagesembed import PagesEmbed, EmbedPagesEmbed, FieldPagesEmbed
from roombot.utils.roomembed import RoomEmbed
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
        await logc("===== FORBIDDEN Error raised from: " + ctx.message.content, bot)
        await logc(error.text, bot)
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
    await logc("===== Error raised from: " + ctx.message.content, bot)
    await logc(error, bot)

    errorText = ''
    try:
        errorText = '```' + str(error) + '```'
    except:
        pass
    finally:
        await ctx.send(errorText + settings.get_text('fatal_error').format(
            settings.prefix + settings.get_text('_commands')['support']['_name']) )


# Periodically check for inactive rooms
async def delete_inactive_rooms():
    for room_data in rooms_db.find():
        r = Room.from_query(room_data)
        if r.timeout and r.timeout > 0:
            guild = bot.get_guild(r.guild)
            birth_channel = guild.get_channel(r.birth_channel) if guild else None
            channel = guild.get_channel(r.channel_id) if guild else None

            if (channel):
                history = (await channel.history(limit=1).flatten())
                if len(history) > 0:
                    last_message = history[0]
                    last_message_datetime = utime(last_message.created_at)
                    voice_channel = guild.get_channel(r.voice_channel_id) if guild else None
                    if voice_channel and len(voice_channel.members) > 0:
                        r.update_active()
                    if last_message_datetime > utime(r.last_active):
                        r.update('last_active', last_message_datetime)

            time_diff = now() - utime(r.last_active)
            if time_diff.total_seconds()/60 >= r.timeout: # timeout is in minutes
                if guild:
                    await r.disband(guild)
                    if birth_channel:
                        settings = Settings.get_for(guild.id)
                        await birth_channel.send(settings.get_text('disband_from_inactivity').format(r.activity))
                else:
                    rooms_db.delete(role_id=self.role_id)
                    invites_db.delete(room_id=self.role_id)


@tasks.loop(seconds=60)
async def delete_inactive():
    try:
        await FieldPagesEmbed.destroy_old()
        await EmbedPagesEmbed.destroy_old()
        await RoomEmbed.destroy_old()
        await delete_inactive_rooms()
    except Exception as e:
        await logc("===== Error raised from: delete_inactive", bot)
        await logc(e, bot)

# add cogs (groups of commands)
cogs = [ 'general', 'basicroom', 'roomhost', 'admin' ]
for cog_name in cogs:
    bot.load_extension('roombot.cogs.' + cog_name)


def run_bot():
    delete_inactive.start()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))