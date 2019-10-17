from utility import *
from discord.ext import commands
import discord

class RoomHost(commands.Cog, name="Room Host"):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.color = discord.Color.blurple()
        self.p_keys = ['player', 'room', 'room_channel', 'room_role', 'flags', 'words', 'new_value', 'mentioned_player']
        self.p = dict.fromkeys(self.p_keys)

    def get_target_player(self, ctx, args):
        log(args)
        name_filter = " ".join(args).lower()
        target_player = self.p['mentioned_player']
        if not target_player:
            for p in ctx.guild.members:
                if p.display_name.lower() == name_filter or p.name.lower() == name_filter:
                    target_player = p
        return target_player

    async def cog_before_invoke(self, ctx, *args):
        self.p['player'] = ctx.message.author
        r = get_hosted_room(self.p['player'].id, ctx.guild.id)
        r.update_active()
        self.p['room'] = r
        self.p['room_channel'] = ctx.guild.get_channel(r.channel_id)
        self.p['room_role'] = ctx.guild.get_role(r.role_id)
        self.p['mentioned_player'] = ctx.message.mentions[0] if ctx.message.mentions else None

    async def cog_after_invoke(self, ctx):
        self.p = dict.fromkeys(self.p_keys)

    async def cog_check(self, ctx):
        return get_hosted_room(ctx.message.author.id, ctx.guild.id)

    async def cog_command_error(self, ctx, error):
        if type(error) == discord.ext.commands.errors.CheckFailure:
            await ctx.send("You are not the host of a room.")


    @commands.command(aliases=['k'])
    async def kick(self, ctx, *args):
        """
        Kick a player.
        Can either mention or use the name of the kickee.
        """
        kickee = self.get_target_player(ctx, args)
        if not kickee:
            return await ctx.send("Please @mention or type the name of the kickee.")
        if self.p['player'].id == kickee.id:
            return await ctx.send("{}, why are you trying to kick yourself?".format(self.p['player'].display_name))
        if kickee.id in self.p['room'].players:
            await self.p['room'].remove_player(kickee)
            await ctx.send("{} has kicked {} from {}.".format(self.p['player'].display_name, kickee.display_name, self.p['room'].activity))
            if len(self.p['room'].players) < 1:
                await self.p['room'].disband(player.guild)
                return await ctx.send("There are no players left in the room. Room has been disbanded.")
        else:
            return await ctx.send("{} is not in your room {}.".format(kickee.display_name, self.p['room_channel'].mention))


    @commands.command(aliases=['h', 'bestow', 'leader'])
    async def host(self, ctx, *args):
        """
        Change the host of your room.
        Can either mention or use the name of new host.
        """
        new_host = self.get_target_player(ctx, args)
        if not new_host:
            return await ctx.send("Please @mention or type the name of the new host.")
        for p in self.p['room'].players:
            if p == new_host.id:
                self.p['room'].host = new_host.id
                rooms.update(dict(role_id=self.p['room'].role_id, host=new_host.id), ['role_id'])
                return await ctx.send("{} is now the new host of {}.".format(new_host.mention, self.p['room_channel'].mention))
        return await ctx.send("{} is not in your room {}.".format(new_host.display_name, self.p['room_channel'].mention))


    @commands.command(aliases=['e', 'change', 'set'])
    async def edit(self, ctx, *args):
        """
        Edit room information using flags.
        For example, `r.edit -activity myNewGame -size 4`.
        You can use aliases (ex. `-a` for `-activity`).
        """
        fields = {
            'activity': self.activity.aliases,
            'description': self.description.aliases,
            'size': self.size.aliases,
            'host': self.host.aliases,
            'colour': self.colour.aliases }
        edits = ' '.join(args).split('-')

        if len(edits) < 2:
            return await ctx.send("Please specify the field(s) using flags (`-activity`, `-description`, `-size`, `-host`).")
        del edits[0] # First index contains useless args before a flag

        for edit in edits:
            words = edit.strip().split(' ')
            valid = False
            f = words[0]
            for field, aliases in fields.items():
                if f == field or f in aliases:
                    f_args = tuple(words[1:])
                    if field == 'activity':
                        await self.activity.callback(self, ctx, *f_args)
                    elif field == 'description':
                        await self.description.callback(self, ctx, *f_args)
                    elif field == 'size':
                        await self.size.callback(self, ctx, *f_args)
                    elif field == 'host':
                        await self.host.callback(self, ctx, *f_args)
                    elif field == 'colour':
                        await self.colour.callback(self, ctx, *f_args)
                    valid = True
                    break
            if not valid:
                await ctx.send("The field `{}` is not recognized.".format(f))


    @commands.command(aliases=['a', 'game', 'name'])
    async def activity(self, ctx, *args):
        """
        Set the name of your room.
        This is what the channel and role will be named as.
        """
        new_activity = ' '.join(args)
        await self.p['room_role'].edit(name="Room - " + new_activity)
        await self.p['room_channel'].edit(name=new_activity)
        self.p['room'].activity = new_activity
        rooms.update(dict(role_id=self.p['room'].role_id, activity=new_activity), ['role_id'])
        return await ctx.send("{} updated activity for {}.".format(self.p['player'].display_name, self.p['room_channel'].mention))


    @commands.command(aliases=['d', 'desc', 'note'])
    async def description(self, ctx, *args):
        """
        Set the description of your room.
        The description is the little message that you will see in the room list.
        """
        new_description = ' '.join(args)
        self.p['room'].description = new_description
        rooms.update(dict(role_id=self.p['room'].role_id, description=new_description), ['role_id'])
        await self.p['room_channel'].edit(topic="({}/{}) {}".format(len(self.p['room'].players), self.p['room'].size, self.p['room'].description))
        return await ctx.send("{} updated the description for {}.".format(self.p['player'].display_name, self.p['room_channel'].mention))


    @commands.command(aliases=['s', 'max', 'players'])
    async def size(self, ctx, *args):
        """
        Set the max player size of your room.
        Once the room is full, I will ping the room.
        """
        new_size = args[0] if args else None
        try:
            if len(self.p['room'].players) > int(new_size):
                return await ctx.send("There are too many players.")
            elif len(self.p['room'].players) == int(new_size):
                await ctx.send("The room is now full.")
            self.p['room'].size = min(abs(int(new_size)), 100) # Max room size is 100
            rooms.update(dict(role_id=self.p['room'].role_id, size=int(new_size)), ['role_id'])
            return await ctx.send("{} updated room size of {} to {}.".format(self.p['player'].display_name, self.p['room_channel'].mention, new_size))
        except ValueError:
            return await ctx.send("The new room size must be an integer.")


    @commands.command(aliases=['c', 'color'])
    async def colour(self, ctx, *args):
        """
        Set the color of your room.
        Possible colors are: teal, green, blue, purple, magenta/pink,
        gold/yellow, orange, and red.
        A random color is set if the specified color is not included above.
        """
        color = get_color(" ".join(args))
        await self.p['room_role'].edit(color=color)
        rooms.update(dict(role_id=self.p['room'].role_id, color=color.value), ['role_id'])
        return await ctx.send("{} updated color for {}.".format(self.p['player'].display_name, self.p['room_channel'].mention))




