from utility import *
from discord.ext import commands
import discord

class BasicRoom(commands.Cog, name="Basic Room"):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.blurple()
        # self.invitee_list = db.get_table('invitees', primary_id='id')
        self.invitee_list = []

    @commands.command(aliases=['n', 'create', 'start'])
    async def new(self, ctx, *args):
        """Make a new room (uses current activity or input)."""
        activity = None
        player = ctx.message.author

        if not args and player.activity:
            activity = player.activity.name
        else:
            activity = " ".join(args)
        
        if not activity:
            return await ctx.send('Please specify the room activity (or start doing something).')
        if not ctx.guild.me.guild_permissions.manage_channels or not ctx.guild.me.guild_permissions.manage_roles:
            raise discord.ext.commands.errors.CommandInvokeError("Missing Permissons")

        rooms_data = rooms.find(guild=ctx.guild.id)
        if rooms_data:
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                if player.id in r.players:
                    return await ctx.send("You are already in a room.")
                if r.activity == activity:
                    activity += " ({})".format(player.name)
                    
        role = await player.guild.create_role(
            name="Room - " + activity,
            color=some_color(),
            hoist=True,
            mentionable=True )
        # await role.edit(position=1)
        existing_category = discord.utils.get(player.guild.categories, name='Rooms')
        category = existing_category if existing_category else await player.guild.create_category('Rooms')
        channel = await player.guild.create_text_channel(activity, category=category, position=0, overwrites={
            player.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            player.guild.me: discord.PermissionOverwrite(read_messages=True),
            role: discord.PermissionOverwrite(read_messages=True) })

        new_room = Room.from_message(activity, ctx, args, role.id, channel.id, role.color)
        new_room.update_active()
        success = await new_room.add_player(player)
        if success:
            emb = new_room.get_embed(player, "New room made")
            await channel.send(create_message(player.display_name))
            return await ctx.send(embed=emb)
        return await ctx.send("There was an error creating the room. Please try again.")


    @commands.command(aliases=['j'])
    async def join(self, ctx, *args):
        """Join a room (by activity or player)."""
        if len(args) < 1:
            return await ctx.send("Please specify a room by activity or player.")
        user_mention_filter = ctx.message.mentions[0].id if ctx.message.mentions else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None
        text_filter = " ".join(args).lower() if args else None

        rooms_data = rooms.find(guild=ctx.guild.id)
        if rooms_data:
            room_match = None
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                if ctx.message.author.id in r.players:
                    return await ctx.send("You are already in a room.")
                    
                player_names = []
                for id in r.players:
                    player = ctx.guild.get_member(id)
                    if player:
                        player_names.append(player.display_name.lower())
                        
                if r.activity.lower() == text_filter or text_filter in player_names or user_mention_filter in r.players or role_mention_filter == r.role_id:
                    room_match = r
                    
            if room_match:
                room_match.update_active()
                player = ctx.message.author
                if await room_match.add_player(player):
                    await ctx.send(embed=room_match.get_embed(player, "Room joined by"))
                    room_channel = ctx.guild.get_channel(room_match.channel_id)
                    await room_channel.send(join_message(player.display_name))

                    if len(room_match.players) >= room_match.size:
                        role = player.guild.get_role(room_match.role_id)
                        await ctx.send("Hey {}! {} players have joined.".format(role.mention, len(room_match.players)))
                        return
                else:
                    return await ctx.send("There was an error joining.")
            else:
                return await ctx.send("That room does not exist.")
        else:
            return await ctx.send("Sorry, no rooms exist yet.")


    @commands.command(aliases=['i'])
    async def invite(self, ctx, *args):
        """Invite a player/players to your room (by name or mention)."""
        if len(args) < 1:
            return await ctx.send("Please specify the name or mention of the invitee.")
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

        rooms_data = rooms.find(guild=ctx.guild.id)
        room_match = None
        if rooms_data:
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                if player.id in r.players:
                    room = r
        if not room:
            return await ctx.send("You are not in a room.")

        if not invitees:
            return await ctx.send("Invite who? (Check if the username is correct?)")
                    
        room.update_active()
        embed = discord.Embed(
            color=discord.Color.blurple(),
            description="Lucky you.",
            timestamp=datetime.now(pytz.utc),
            title=invite_message(player.display_name, room.activity) )
        embed.add_field(
            name="Players ({}/{})".format(len(room.players), room.size),
            value="<@{}>".format(">, <@".join([str(id) for id in room.players])) )
        embed.add_field(
            name="Inviter: " + player.display_name,
            value="Server: " + player.guild.name )
        embed.add_field(
            name="Room: " + room.activity,
            value="Note: " + room.description )
        embed.add_field(
            name="Room ID",
            value=room.role_id )
        embed.set_footer(
            text="React to accept or decline the invite.",
            icon_url=discord.Embed.Empty )


        result_embed = discord.Embed(
            color=discord.Color.blurple(),
            description="for room: `{}`".format(room.activity),
            timestamp=datetime.now(pytz.utc),
            title="Invites Sent" )
        result_embed.set_footer(
            text="Invites sent by: " + player.display_name,
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
                name="Invitees",
                value="<@{}>".format(">, <@".join([str(id) for id in invitee_success])) )
        if invitee_fail:
            result_embed.add_field(
                name="Failed invites",
                value="I was unable to access these folks, probably because of their settings or because they are a bot.\n<@{}>".format(">, <@".join([str(id) for id in invitee_fail])) )
        if invitee_already_joined:
            result_embed.add_field(
                name="Already joined",
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
            if field.name == "Room ID":
                room_id = field.value
                break
        room = None
        room_data = rooms.find_one(role_id=room_id)
        if room_data:
            room = Room.from_query(room_data)
        if not room:
            return await channel.send("Room no longer exists.")

        if (accept):
            if player.id in room.players:
                return await channel.send("You are already in that room.")
            await channel.send("Invite accepted.")
            room.update_active()
            guild = self.bot.get_guild(room.guild)
            player = guild.get_member(player.id)
            if not guild:
                return await channel.send("I am not in that server anymore :(")
            if await room.add_player(player):
                await channel.send(embed=room.get_embed(player, "Room joined by"))
                room_channel = guild.get_channel(room.channel_id)
                await room_channel.send(join_message(player.display_name))

                if len(room.players) >= room.size:
                    role = guild.get_role(room.role_id)
                    room_channel = guild.get_channel(room.channel_id)
                    await room_channel.send("Hey {}! {} players have joined.".format(role.mention, len(room.players)))
        else:
            await channel.send("Invite declined.")
                


    @commands.command(aliases=['x', 'exit', 'disband'])
    async def leave(self, ctx):
        """Leave a room. If you are the host, the room will be disbanded."""
        player = ctx.message.author
        rooms_data = rooms.find(guild=ctx.guild.id)
        if rooms_data:
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                if r.host == player.id:
                    r.update_active()
                    role = player.guild.get_role(r.role_id)
                    await r.disband(player.guild)
                    try:
                        await ctx.send("{}'s room `{}` has been disbanded.".format(player.display_name, r.activity))
                    except discord.errors.NotFound as e:
                        log(e)
                        
                    return
                elif player.id in r.players:
                    r.update_active()
                    await r.remove_player(player)
                    await ctx.send("{} has left `{}`".format(player.name, r.activity))
                    if len(r.players) < 1:
                        await r.disband(player.guild)
                        return await ctx.send("There are no players left in the room. Room has been disbanded.")
                    return
        return await ctx.send("{}, you cannot leave a room if you are not in one.".format(player.display_name))


    @commands.command(aliases=['rooms', 'list', 'dir'])
    async def ls(self, ctx):
        """List rooms in current guild."""
        rooms_data = rooms.find(guild=ctx.guild.id)
        embed = discord.Embed(color=discord.Color.blurple(), title="Rooms")
        exists = False

        for room_data in rooms_data:
            exists = True
            room = Room.from_query(room_data)

            description = room.description if room.description else 'Players: ' + ', '.join(room.players)
            embed.add_field(
                name="{0} ({1}/{2})".format(room.activity, len(room.players), room.size),
                value=description )
        if exists:
            await ctx.send(embed=embed)
        else:
            await ctx.send("No rooms exist yet.")


    @commands.command(aliases=['r', 'room'])
    async def look(self, ctx, *args):
        """Shows your current room (or look at another room by activity or player)."""
        player_name = ctx.message.author.display_name
        rooms_data = rooms.find(guild=ctx.guild.id)
        player_filter = ctx.message.mentions[0].id if ctx.message.mentions else ctx.message.author.id
        activity_filter = " ".join(args) if args else None
        role_mention_filter = ctx.message.role_mentions[0].id if ctx.message.role_mentions else None

        rooms_data = rooms.find(guild=ctx.guild.id)
        if rooms_data:
            for room_data in rooms_data:
                r = Room.from_query(room_data)
                if player_filter in r.players or r.activity == activity_filter or r.role_id == role_mention_filter:
                    r.update_active()
                    return await ctx.send(embed=r.get_embed(ctx.author, "Request")) 
        else:
            return await ctx.send("Oh {}, looks like no rooms exist yet.".format(player_name))
        
        return await ctx.send("Sorry {}, I could not find your room.".format(player_name))


