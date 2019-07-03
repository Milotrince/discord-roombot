import dataset
from random import choice
from datetime import datetime, timedelta
import discord

# Start database
db = dataset.connect('sqlite:///:memory:')
rooms = db.get_table('rooms', primary_id='role_id')

class Room:
    def __init__(self, role_id, channel_id, color, birth_channel, guild, activity,
                 description, created, timeout, players, host, size, last_active):
        self.role_id = role_id
        self.channel_id = channel_id
        self.color = color
        self.birth_channel = birth_channel
        self.guild = guild
        self.activity = activity
        self.description = description
        self.created = created
        self.timeout = timeout
        self.players = players
        self.host = host
        self.size = size
        self.last_active = last_active

        rooms.upsert(dict(
            role_id=role_id,
            channel_id=channel_id,
            color=color,
            birth_channel=birth_channel,
            guild=guild,
            activity=activity,
            description=description,
            created=created,
            timeout=timeout,
            players=ids_to_str(players),
            host=host,
            size=size,
            last_active=last_active ), ['role_id'])
            
    @classmethod
    def from_message(cls, activity, ctx, args, role_id, channel_id, color):
        """Create a Room from a message"""
        default_descriptions = [
            "Let's do something together",
            "Join me, I'm cool",
            "Why not?",
            "Let's play!" ]

        # role_id = role_id
        # channel_id = channel_id
        guild = ctx.message.guild.id
        color = color.value
        birth_channel = ctx.message.channel.id
        # activity = activity
        description = choice(default_descriptions)
        created = datetime.now()
        timeout = 60 * 60
        players = []
        host = ctx.message.author.id
        size = 2
        last_active = datetime.now()
        return cls(role_id, channel_id, color, birth_channel, guild, activity, description,
                   created, timeout, players, host, size, last_active)
            
    @classmethod
    def from_query(cls, data):
        """Create a Room from a query"""
        role_id = data['role_id']
        channel_id = data['channel_id']
        color = data['color']
        birth_channel = data['birth_channel']
        guild = data['guild']
        activity = data['activity']
        description = data['description']
        created = data['created']
        timeout = data['timeout']
        players = str_to_ids(data['players'])
        host = data['host']
        size = data['size']
        last_active = data['last_active']
        return cls(role_id, channel_id, color, birth_channel, guild, activity, description,
                   created, timeout, players, host, size, last_active)
                   

    def get_embed(self, guild):
        """Generate a discord.Embed for this room"""
        description = discord.Embed.Empty if self.description == '' else self.description
        room_status = "Waiting for {} more players".format(self.size - len(self.players)) if len(self.players) < self.size else "Room is full"
        player_names = []
        for id in self.players:
            player = guild.get_member(id)
            if player:
                player_names.append(player.name)

        embed = discord.Embed(
            color=self.color,
            description=description,
            timestamp=self.created,
            title=self.activity )
        embed.add_field(
            name="Players ({}/{})".format(len(self.players), self.size),
            value=", ".join(player_names) )
        embed.add_field(
            name=room_status,
            value="Room will automatically disband from inactivity." )
        embed.set_footer(
            text="Host: {}".format(guild.get_member(self.host).name),
            icon_url=discord.Embed.Empty )
        
        return embed


    def update_active(self):
        self.last_active = datetime.now()
        rooms.update(dict(role_id=self.role_id, last_active=self.last_active), ['role_id'])


    async def add_player(self, player):
        """Add a player to this room"""
        if player.id not in self.players:
            role = player.guild.get_role(self.role_id)
            if role:
                await player.add_roles(role)
                self.players.append(player.id)
                rooms.update(dict(role_id=self.role_id, players=ids_to_str(self.players)), ['role_id'])
                return True
        return False

    async def remove_player(self, player):
        """Remove a player from this room"""
        if player.id in self.players:
            role = player.guild.get_role(self.role_id)
            await player.remove_roles(role)
            self.players.remove(player.id)
            rooms.update(dict(role_id=self.role_id, players=ids_to_str(self.players)), ['role_id'])
            return True
        return False

    async def disband(self, guild):
        """Delete room"""
        role = guild.get_role(self.role_id)
        for id in self.players:
            player = guild.get_member(id)
            await self.remove_player(player)
        rooms.delete(role_id=self.role_id)
        await role.delete()

        channel = guild.get_channel(self.channel_id)
        await channel.delete()


def ids_to_str(ids, seperator=','):
    """Turn a list of ints into a database inputable string"""
    return seperator.join([ str(id) for id in ids ])

def str_to_ids(s):
    """Turn a string of comma seperated ints from a database into a list of ints"""
    return [ int(id) for id in s.split(',') ] if s else []