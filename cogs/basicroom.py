from room import *
from discord.ext import commands
import discord

def filterBots(member):
    return member.bot

class BasicRoom(commands.Cog, name=strings['_cog']['room']):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.blurple()
        # self.invitee_list = db.get_table('invitees', primary_id='id')
        self.invitee_list = []

    @commands.command(aliases=strings['_aliases']['new'])
    async def new(self, ctx, *args):
        """Make a new room (uses current activity or input)."""
        activity = None
        player = ctx.message.author

        if args:
            activity = " ".join(args)
        elif player.activity:
            activity = player.activity.name
        else:
            activity = choice(strings['default_room_names']).format(player.display_name)
        
        if not ctx.guild.me.guild_permissions.manage_channels or not ctx.guild.me.guild_permissions.manage_roles:
            raise discord.ext.commands.errors.CommandInvokeError("Missing Permissons")

        rooms = rooms_db.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if player.id in r.players:
                    return await ctx.send(strings['already_in_room'])
                if r.activity == activity:
                    activity += " ({})".format(player.name)
                    
        role = await player.guild.create_role(
            name="(Room) " + activity,
            color=some_color(),
            hoist=True,
            mentionable=True )

        settings = Settings.get_for(ctx.guild.id)
        accessors_ids = settings.access_all_rooms_role
        accessors = []
        for accessor_id in accessors_ids:
            log(accessor_id)
            accessor_player = ctx.guild.get_member(accessor_id)
            accessor_role = ctx.guild.get_role(accessor_id)
            if accessor_player:
                accessors.append(accessor_player)
            elif accessor_role:
                accessors.append(accessor_role)
        if len(accessors) < 1:
            accessors = list(filter(filterBots, ctx.guild.members))

        overwrites = {
            player.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            player.guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True),
            role: discord.PermissionOverwrite(read_messages=True)
        }
        for accessor in accessors:
            overwrites[accessor] = discord.PermissionOverwrite(read_messages=True)

        category = await get_rooms_category(player.guild)
        channel = await player.guild.create_text_channel(
            activity,
            category=category,
            position=0,
            overwrites=overwrites
        )
        voice_channel = None
        if settings.voice_channel:
            voice_channel = await player.guild.create_voice_channel(
                activity,
                bitrate=settings.bitrate * 1000,
                category=category,
                position=0,
                overwrites=overwrites
            )

        new_room = Room.from_message(ctx, args, settings, activity, role, channel, voice_channel)
        
        success = await new_room.add_player(player)
        if success:
            emb = new_room.get_embed(player, strings['new_room'])
            await channel.send(choice(strings['new_room_welcomes']).format(player.display_name))
            return await ctx.send(embed=emb)
        return await ctx.send(strings['retry_error'])


    @commands.command(aliases=strings['_aliases']['join'])
    async def join(self, ctx, *args):
        """Join a room (by activity or player)."""
        if len(args) < 1:
            return await ctx.send(strings['missing_target_room'])
        user_mention_filter = ctx.message.mentions[0].id if ctx.message.mentions else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None
        text_filter = " ".join(args).lower() if args else None

        rooms = rooms_db.find(guild=ctx.guild.id)
        if rooms:
            room_match = None
            for room_data in rooms:
                r = Room.from_query(room_data)
                if ctx.message.author.id in r.players:
                    return await ctx.send(strings['already_in_room'])
                    
                player_names = []
                for id in r.players:
                    player = ctx.guild.get_member(id)
                    if player:
                        player_names.append(player.display_name.lower())
                        
                if r.activity.lower() == text_filter or text_filter in player_names or user_mention_filter in r.players or role_mention_filter == r.role_id:
                    room_match = r
                    
            if room_match:
                room_match.update_active()
                if (room_match.lock):
                    return await ctx.send(strings['join_locked_room'])
                if (room_match.size <= len(room_match.players)):
                    return await ctx.send(strings['join_full_room'])
                player = ctx.message.author
                if await room_match.add_player(player):
                    await ctx.send(embed=room_match.get_embed(player, strings['room_joined']))
                    room_channel = ctx.guild.get_channel(room_match.channel_id)
                    await room_channel.send(choice(strings['join_messages']).format(player.display_name))
                    if len(room_match.players) >= room_match.size:
                        role = player.guild.get_role(room_match.role_id)
                        await ctx.send(strings['full_room_notification'].format(role.mention, len(room_match.players)))
                        return
                    return
                else:
                    return await ctx.send(strings['retry_error'])

        return await ctx.send(strings['room_not_exist'])


    @commands.command(aliases=strings['_aliases']['invite'])
    async def invite(self, ctx, *args):
        """Invite a player/players to your room (by name or mention)."""
        if len(args) < 1:
            return await ctx.send(strings['missing_target'])
        user_mentions = ctx.message.mentions
        role_mentions = ctx.message.role_mentions
        player = ctx.message.author
        invitees = []
        room = None
        
        for invitee in user_mentions:
            if invitee.id not in invitees:
                invitees.append(invitee.id)

        for role in role_mentions:
            for member in role.members:
                if member.id not in invitees:
                    invitees.append(member.id)

        player_names = []
        for member in ctx.guild.members:
            player_names.append(member.display_name.lower())
            player_names.append(member.name.lower())

        for arg in args:
            if arg in player_names:
                p = discord.utils.find(lambda p: p.name.lower() == arg.lower(), ctx.guild.members)
                if p and p.id not in invitees:
                    invitees.append(p.id)

        rooms = rooms_db.find(guild=ctx.guild.id)
        room_match = None
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if player.id in r.players:
                    room = r
        if not room:
            return await ctx.send(strings['not_in_room'])

        if not invitees:
            return await ctx.send(strings['missing_target_invitees'])
                    
        room.update_active()
        embed = discord.Embed(
            color=discord.Color.blurple(),
            timestamp=datetime.now(pytz.utc),
            title=choice(strings['invite_messages']).format(player.display_name, room.activity) )
        embed.add_field(
            name="{} ({}/{})".format(strings['players'], len(room.players), room.size),
            value="<@{}>".format(">, <@".join([str(id) for id in room.players])) )
        embed.add_field(
            name=strings['inviter'] + ": " + player.display_name,
            value=strings['server'] + ": " + player.guild.name )
        embed.add_field(
            name=strings['room'] + ": " + room.activity,
            value=strings['description'] + ": " + room.description )
        embed.add_field(
            name="ID",
            value=room.role_id )
        embed.set_footer(
            text=strings['invite_instructions'],
            icon_url=discord.Embed.Empty )


        result_embed = discord.Embed(
            color=discord.Color.blurple(),
            description="{}: `{}`".format(strings['room'], room.activity),
            timestamp=datetime.now(pytz.utc),
            title=strings['invites_sent'] )
        result_embed.set_footer(
            text="{}: {}".format(strings['inviter'], player.display_name),
            icon_url=discord.Embed.Empty )
        invitee_success = []
        invitee_fail = []
        invitee_already_joined = []
        for invitee_id in invitees:
            try:
                if invitee_id in room.players:
                    invitee_already_joined.append(invitee_id)
                    continue
                invitee = self.bot.get_user(invitee_id)
                m = await invitee.send(embed=embed)
                await m.add_reaction('✅')
                await m.add_reaction('❌')
                self.invitee_list.append(invitee_id)
                invitee_success.append(invitee_id)
            except discord.errors.Forbidden as e:
                invitee_fail.append(invitee_id)

        if invitee_success:
            result_embed.add_field(
                name=strings['invitees'],
                value="<@{}>".format(">, <@".join([str(id) for id in invitee_success])) )
        if invitee_fail:
            result_embed.add_field(
                name=strings['failed_invites'],
                value="{}\n<@{}>".format(strings['failed_invites_description'], ">, <@".join([str(id) for id in invitee_fail])) )
        if invitee_already_joined:
            result_embed.add_field(
                name=strings['already_joined'],
                value="<@{}>".format(">, <@".join([str(id) for id in invitee_already_joined])) )
            
        return await ctx.send(embed=result_embed)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        player = user
        channel = reaction.message.channel
        accept = reaction.emoji == '✅'
        decline = reaction.emoji == '❌'
        valid_invite_emoji = accept or decline
        from_dm = type(channel) is discord.channel.DMChannel
        if not valid_invite_emoji or player.id not in self.invitee_list or not from_dm:
            return

        self.invitee_list.remove(player.id)
        room_id = None
        for field in reaction.message.embeds[0].fields:
            if field.name == "ID":
                room_id = field.value
                break
        room = None
        room_data = rooms_db.find_one(role_id=room_id)
        if room_data:
            room = Room.from_query(room_data)
        if not room:
            return await channel.send(strings['room_not_exist'])

        if (accept):
            guild = self.bot.get_guild(room.guild)

            if not guild:
                return await channel.send(strings['room_not_exist'])
            player = guild.get_member(player.id)
            if player.id in room.players:
                return await channel.send(strings['already_in_room'])
            rooms = rooms_db.find(guild=guild.id)
            if rooms:
                for room_data in rooms:
                    r = Room.from_query(room_data)
                    if player.id in r.players:
                        return await channel.send(strings['already_in_room'])

            await channel.send(strings['invite_accepted'])
            room.update_active()
            if await room.add_player(player):
                await channel.send(embed=room.get_embed(player, strings['room_joined']))
                room_channel = guild.get_channel(room.channel_id)
                await room_channel.send(choice(strings['join_messages']).format(player.display_name))

                if len(room.players) >= room.size:
                    role = guild.get_role(room.role_id)
                    room_channel = guild.get_channel(room.channel_id)
                    await room_channel.send(strings['full_room_notification'].format(role.mention, len(room.players)))
        else:
            await channel.send(strings['invite_declined'])
                


    @commands.command(aliases=strings['_aliases']['leave'])
    async def leave(self, ctx):
        """Leave a room. If you are the host, the room will be disbanded."""
        player = ctx.message.author
        rooms = rooms_db.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if r.host == player.id:
                    r.update_active()
                    role = player.guild.get_role(r.role_id)
                    await r.disband(player.guild)
                    try:
                        await ctx.send(strings['disband_room'].format(player.display_name, r.activity))
                    except discord.errors.NotFound as e:
                        log(e)
                        
                    return
                elif player.id in r.players:
                    r.update_active()
                    await r.remove_player(player)
                    await ctx.send(strings['left_room'].format(player.name, r.activity))
                    if len(r.players) < 1:
                        await r.disband(player.guild)
                        return await ctx.send(strings['disband_empty_room'])
                    return
        return await ctx.send(strings['not_in_room'])


    @commands.command(aliases=strings['_aliases']['ls'])
    async def ls(self, ctx):
        """List rooms in current guild."""
        rooms = rooms_db.find(guild=ctx.guild.id)
        embed = discord.Embed(color=discord.Color.blurple(), title="Rooms")
        exists = False

        for room_data in rooms:
            exists = True
            room = Room.from_query(room_data)

            description = room.description if room.description else "{}: {}".format(strings['players'], ', '.join(room.players))
            embed.add_field(
                name="{}{} ({}/{})".format(":lock: " if room.lock else "", room.activity, len(room.players), room.size),
                value=description )
        if exists:
            await ctx.send(embed=embed)
        else:
            await ctx.send(strings['no_rooms'])


    @commands.command(aliases=strings['_aliases']['look'])
    async def look(self, ctx, *args):
        """Shows your current room (or look at another room by activity or player)."""
        player_name = ctx.message.author.display_name
        rooms = rooms_db.find(guild=ctx.guild.id)
        player_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
        activity_filter = " ".join(args) if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms = rooms_db.find(guild=ctx.guild.id)
        if rooms:
            for room_data in rooms:
                r = Room.from_query(room_data)
                if player_filter in r.players or r.activity == activity_filter or r.role_id == role_mention_filter:
                    r.update_active()
                    return await ctx.send(embed=r.get_embed(ctx.author, strings['request'])) 
        else:
            return await ctx.send(strings['no_rooms'])
        
        return await ctx.send(strings['no_room'])


def setup(bot):
    bot.add_cog(BasicRoom(bot))