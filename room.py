import dataset
from datetime import datetime, timedelta
import discord

# Start database
db = dataset.connect('sqlite:///:memory:')
rooms = db.get_table('rooms', primary_id='role_id')

class Room:
    def __init__(self, role_id, guild, activity, description, created, timeout, players, host, waiting_for):
        self.role_id = role_id
        self.guild = guild
        self.activity = activity
        self.description = description
        self.created = created
        self.timeout = timeout
        self.players = players
        self.host = host
        self.waiting_for = waiting_for

        rooms.upsert(dict(
            role_id=role_id,
            guild=guild,
            activity=activity,
            description=description,
            created=created,
            timeout=timeout,
            players='\\'.join(players),
            host=host,
            waiting_for=waiting_for ), ['role_id'])
            
    @classmethod
    def from_message(cls, activity, ctx, args, role_id):
        """Create a Room from a message"""
        # role_id = role_id
        guild = ctx.message.guild.id
        # activity = activity
        description = ''
        created = datetime.now()
        timeout = 60 * 60
        players = []
        host = ctx.message.author.name
        waiting_for = 2
        return cls(role_id, guild, activity, description, created, timeout, players, host, waiting_for)
            
    @classmethod
    def from_query(cls, data):
        """Create a Room from a query"""
        role_id = data['role_id']
        guild = data['guild']
        activity = data['activity']
        description = data['description']
        created = data['created']
        timeout = data['timeout']
        players = data['players'].split('\\')
        host = data['host']
        waiting_for = data['waiting_for']
        return cls(role_id, guild, activity, description, created, timeout, players, host, waiting_for)

    def get_embed(self):
        """Generate a discord.Embed for this room"""
        description = discord.Embed.Empty if self.description == '' else self.description
        # TODO: format time
        # TODO: disband if remaining time 0
        remaining_time = self.created + timedelta(seconds=self.timeout) - datetime.now()

        embed = discord.Embed(
            color=discord.Color.blue(),
            description=description,
            timestamp=self.created,
            title=self.activity )
        embed.add_field(
            name="Players ({0})".format(len(self.players)),
            value=", ".join(self.players) )
        embed.add_field(
            name="Waiting for {0} players".format(self.waiting_for),
            value="Room will disband in {0}".format(remaining_time) )
        embed.set_footer(
            text="Host: {0}".format(self.host),
            icon_url=discord.Embed.Empty )
        
        return embed

    async def add_player(self, player):
        """Add a player to this room"""
        if player.name not in self.players:
            role = player.guild.get_role(self.role_id)
            await player.add_roles(role)
            if role:
                self.players.append(player.name)
                rooms.update(dict(role_id=self.role_id, players='\\'.join(self.players)), ['role_id'])
                return True
        return False

    async def remove_player(self, player):
        """Remove a player from this room"""
        if player.name in self.players:
            role = player.guild.get_role(self.role_id)
            await player.remove_roles(role)
            self.players.remove(player.name)
            rooms.update(dict(role_id=self.role_id, players='\\'.join(self.players)), ['role_id'])
            return True
        return False

    async def disband(self, guild):
        """Delete room"""
        role = guild.get_role(self.role_id)
        for player_name in self.players:
            player = guild.get_member_named(player_name)
            await self.remove_player(player)
        rooms.delete(role_id=self.role_id)
        await role.delete()

    async def update(self, player, field, new_value):
        """Update a field of this room"""
        role = player.guild.get_role(self.role_id)
        if field == 'activity':
            await role.edit(name=new_value)
            self.activity = new_value
            rooms.update(dict(role_id=self.role_id, activity=new_value), ['role_id'])
        elif field == 'description':
            self.description = new_value
            rooms.update(dict(role_id=self.role_id, description=new_value), ['role_id'])
        elif field == 'waiting_for':
            self.waiting_for = new_value
            rooms.update(dict(role_id=self.role_id, waiting_for=new_value), ['role_id'])
        elif field == 'host':
            for p in self.players:
                if p == new_value:
                    self.host = new_value
                    rooms.update(dict(role_id=self.role_id, host=new_value), ['role_id'])
                    return True
            return False
        else:
            return False
        return True