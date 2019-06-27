import dataset
from datetime import datetime, timedelta
import discord

# Start database
db = dataset.connect('sqlite:///:memory:')
rooms = db['rooms']

class Room:
    def __init__(self, guild, activity, description, created, timeout, players, host, waiting_for):
        self.guild = guild
        self.activity = activity
        self.description = description
        self.created = created
        self.timeout = timeout
        self.players = players
        self.host = host
        self.waiting_for = waiting_for
        self.id = rooms.insert(dict(
            guild=guild,
            activity=activity,
            description=description,
            created=created,
            timeout=timeout,
            players='\\'.join(players),
            host=host,
            waiting_for=waiting_for ))
            
    @classmethod
    def from_message(cls, activity, ctx, args):
        """Create a Room from a message"""
        guild = ctx.message.guild.id
        activity = activity
        description = args[1] if len(args) > 1 else ''
        created = datetime.now()
        timeout = 60 * 60
        players = [ctx.message.author.name]
        host = ctx.message.author.name
        waiting_for = args[2] if len(args) > 2 else 2
        return cls(guild, activity, description, created, timeout, players, host, waiting_for)
            
    @classmethod
    def from_query(cls, data):
        """Create a Room from a query"""
        guild = data['guild']
        activity = data['activity']
        description = data['description']
        created = data['created']
        timeout = data['timeout']
        players = data['players'].split('\\')
        host = data['host']
        waiting_for = data['waiting_for']
        return cls(guild, activity, description, created, timeout, players, host, waiting_for)

    def get_embed(self):
        """Generate a discord.Embed for this room"""
        description = discord.Embed.Empty if self.description == '' else self.description
        # TODO: format time
        remaining_time = datetime.now() - self.created + timedelta(seconds=self.timeout)

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

    def add_player(self, name):
        """Add a player to this room"""
        if name not in self.players:
            self.players.append(name)
            rooms.update(dict(id=self.id, players='\\'.join(self.players)), ['id'])
            return True
        return False