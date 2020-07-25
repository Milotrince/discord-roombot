import discord
from roombot.utils.functions import now
from roombot.utils.constants import JOIN_EMOJI
from roombot.database.settings import Settings

class RoomEmbed():
    instances = {}

    def __init__(self, ctx, room, footer_text_key, settings):
        self.ctx = ctx
        self.room = room
        self.settings = settings
        self.footer_text = settings.get_text(footer_text_key)
        self.time = now()
        self.timeout = 60 * 30 # 30 min
        self.is_dm = ctx.channel.type is discord.ChannelType.private
        self.m = None

    def make_timed_out_embed(self):
        return discord.Embed(
            color=discord.Color.greyple(),
            title=self.get_text('room')
        ).set_footer(
            text="{}: {} | {}".format(self.footer_text, self.ctx.author.display_name, self.get_text('timed_out')),
            icon_url=discord.Embed.Empty)

    def get_text(self, key):
        return self.settings.get_text(key)

    def get_embed(self):
        description = discord.Embed.Empty if self.room.description == '' else self.room.description
        room_status = self.get_text('room_status').format(self.room.size - len(self.room.players)) if len(self.room.players) < self.room.size else self.get_text('full_room')
        return discord.Embed(
            color=self.room.color,
            description=description,
            timestamp=self.room.created,
            title="{}{}".format(":lock: " if self.room.lock else "", self.room.activity)
        ).add_field(
            name="{} ({}/{})".format(self.get_text('players'), len(self.room.players), self.room.size),
            value="<@{}>".format(">, <@".join([str(id) for id in self.room.players]))
        ).add_field(
            name=self.get_text('host'),
            value="<@{}>".format(self.room.host)
        ).add_field(
            name=self.get_text('channel'),
            value="<#{}>".format(self.room.channel_id)
        ).add_field(
            name=room_status,
            value=self.get_text('room_timeout_on').format(self.room.timeout) if self.room.timeout > 0 else self.get_text('room_timeout_off')
        ).set_footer(
            text="{}: {}".format(self.footer_text, self.ctx.author.display_name),
            icon_url=discord.Embed.Empty)

    async def send(self):
        self.m = await self.ctx.channel.send(embed=self.get_embed())
        RoomEmbed.instances[self.m.id] = self
        if not self.is_dm and not self.room.lock:
            await self.m.add_reaction(JOIN_EMOJI)

    async def self_destruct(self):
        if self.m and self.m.id in RoomEmbed.instances:
            del RoomEmbed.instances[self.m.id]
        embed = self.make_timed_out_embed()
        try:
            await self.m.edit(embed=embed)
            if not self.is_dm:
                await self.m.clear_reactions()
        except:
            pass


    @classmethod
    async def destroy_room(cls, room_id):
        to_destroy = []
        for instance in cls.instances.values():
            if instance.room.role_id == room_id:
                to_destroy.append(instance)
        for instance in to_destroy:
            await instance.self_destruct()

    @classmethod
    async def delete_old(cls):
        to_destroy = []
        for instance in cls.instances.values():
            if (now() - instance.time).total_seconds() > instance.timeout:
                to_destroy.append(instance)
        for instance in to_destroy:
            await instance.self_destruct()

    @classmethod
    async def update(cls, room):
        try:
            for b in cls.instances.values():
                if b.room.role_id == room.role_id:
                    was_locked = b.room.lock
                    b.room = room
                    embed = b.get_embed()
                    await b.m.edit(embed=embed)
                    if not b.room.lock and was_locked:
                        await b.m.add_reaction(JOIN_EMOJI)
                    elif b.room.lock and not was_locked:
                        await b.m.clear_reaction(JOIN_EMOJI)
        except:
            pass # fail silently
