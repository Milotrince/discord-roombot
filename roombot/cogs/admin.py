import discord
from discord.ext import commands
from roombot.database.room import Room
from roombot.database.settings import Settings
from roombot.utils.functions import load_cog, pop_flags, iter_len
from roombot.utils.text import langs, get_text
from roombot.utils.pagesembed import FieldPagesEmbed

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.red()

    async def cog_check(self, ctx):
        return ctx.message.author.guild_permissions.administrator

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            settings = Settings.get_for(ctx.guild.id)
            await ctx.send(settings.get_text('not_admin'))


    @commands.command()
    @commands.guild_only()
    async def reset_settings(self, ctx):
        settings = Settings.get_for(ctx.guild.id)
        settings = Settings(Settings.defaults,
            guild_id=ctx.guild.id,
            language=settings.language,
            prefix=settings.prefix )
        await ctx.send(settings.get_text('reset_settings'))


    # TODO: create_on_react
    # @commands.command()
    # async def create_on_react(self, ctx, *args):
    #     settings = Settings.get_for(ctx.guild.id)

    @commands.command()
    @commands.guild_only()
    async def settings(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        settings_info = {}
        for key in Settings.defaults.keys():
            text = settings.get_text('_commands')[key]
            settings_info[key] = {
                'name': text['_name'],
                'flags': text['_aliases'],
                'description': text['_help']
            }

        (flags, flag_args) = pop_flags(args)
        if flags:
            # set settings
            for i, flag in enumerate(flags):
                for field_name, field in settings_info.items():
                    if flag in field['flags'] + [field['name']]:
                        (success, message) = settings.set(ctx, field_name, flag_args[i])
                        await ctx.send(message)
        else:
            # show settings embed
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=settings.get_text('settings'),
                description=settings.get_text('settings_instructions').format(settings.prefix) )
            for field_name, field in settings_info.items():
                field_value = settings.get(field_name)
                if isinstance(field_value, bool): 
                    field_value = str(int(field_value))
                elif isinstance(field_value, list):
                    field_value = '[`\n'+'\n'.join(['  `'+str(s).replace('`{}`', '__')+'`,' for s in field_value])+'\n`]' if len(field_value) > 0 else '[]'

                embed_desc = "{}: `-{}`\n{}".format(settings.get_text('flags'), "`, `-".join(field['flags']), '\n'.join(field['description']))
                if isinstance(field_value, str) and len(field_value) > 200:
                    embed.add_field(
                        inline=False,
                        name="**{}** : `{}`".format(field['name'], settings.get_text('see_below')),
                        value=(f'{embed_desc}\n`{field_value}')[:1023-4]+'`' )
                else:
                    embed.add_field(
                        inline=False,
                        name="**{}** : `{}`".format(field['name'], field_value),
                        value=embed_desc )

            await FieldPagesEmbed(ctx, embed).send()



    @commands.command()
    @commands.guild_only()
    async def force_disband(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        rooms = Room.find(guild=ctx.guild.id)
        activity_filter = " ".join(args) if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = Room.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if r.activity == activity_filter or r.role_id == role_mention_filter:
                    await r.disband(ctx.guild)
                    try:
                        await ctx.send(settings.get_text('disband_room').format('<@'+str(r.host)+'>', r.activity))
                    except discord.errors.NotFound as e:
                        pass
                    return
        return await ctx.send(settings.get_text('room_not_exist'))


    @commands.command()
    @commands.guild_only()
    async def purge(self, ctx, *args):
        settings = Settings.get_for(ctx.guild.id)
        player = ctx.message.author
        if not player.guild_permissions.administrator:
            return await ctx.send(settings.get_text('not_admin'))

        (flags, words) = pop_flags(args)
        if 'a' not in flags and 'b' not in flags:
            return await ctx.send(settings.get_text('purge_missing_flag'))

        if 'a' in flags:
            rooms_data = Room.find(guild=ctx.guild.id)
            count = 0
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                guild = self.bot.get_guild(r.guild)
                await r.disband(guild)
                count += 1
            await ctx.send(settings.get_text('purged_a').format(count))

        if 'b' in flags:
            deleted_channels = 0
            deleted_roles = 0
            failed_channels = 0
            failed_roles = 0
            category = discord.utils.get(player.guild.categories, name=settings.category_name)
            if not category:
                return await ctx.send(settings.get_text('no_category'))
            for channel in category.channels:
                if iter_len(Room.find(guild=ctx.guild.id, channel_id=channel.id)) < 1:
                    try:
                        await channel.delete()
                        deleted_channels += 1
                    except:
                        failed_channels += 1
            for role in ctx.guild.roles:
                if iter_len(Room.find(guild=ctx.guild.id, role_id=role.id)) < 1:
                    if any([ role.name.startswith('({})'.format(get_text('room', lang=l))) for l in langs ]):
                        try:
                            await role.delete()
                            deleted_roles += 1
                        except:
                            failed_roles += 1

            await ctx.send(settings.get_text('purged_b').format(deleted_channels, deleted_roles))
            if failed_channels > 0 or failed_roles > 0:
                await ctx.send(settings.get_text('purged_b_fail').format(failed_channels, failed_roles))


def setup(bot):
    load_cog(bot, Admin(bot))