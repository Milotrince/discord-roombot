from utils.functions import *
from math import ceil

FIRST_EMOJI = '\u23EE'
PREV_EMOJI = '\u2B05'
NEXT_EMOJI = '\u27A1'
LAST_EMOJI = '\u23ED'
STOP_EMOJI = '\u23F9'
EMOJIS = [FIRST_EMOJI, PREV_EMOJI, NEXT_EMOJI, LAST_EMOJI, STOP_EMOJI]

class PagesEmbed:
    instances = {}

    def __init__(self, ctx, embed, fields_per_page=3):
        self.m = None
        self.time = now()
        self.ctx = ctx
        self.embed = embed
        self.per = fields_per_page
        self.pages = ceil(len(embed.fields)/fields_per_page) - 1
        self.page = 1

    def embed_copy(self):
        return discord.Embed(**self.embed.to_dict())

    def get_req_text(self):
        return get_text('request')+': '+self.ctx.author.display_name

    def make_page(self, i):
        i = clamp(i, 1, self.pages)
        self.page = i
        embed = self.embed_copy()
        page_text = get_text('page').format(i, self.pages)
        embed.set_footer(text=self.get_req_text()+' | '+page_text)
        for j in range(self.per):
            k = i * self.per + j - 1
            if k < len(self.embed.fields):
                field = self.embed.fields[k]
                embed.add_field(inline=field.inline, name=field.name, value=field.value)
        return embed

    async def send(self):
        self.m = await self.ctx.send(embed=self.make_page(1))
        for emoji in EMOJIS:
            await self.m.add_reaction(emoji)
        PagesEmbed.instances[self.m.id] = self

    async def self_destruct(self):
        if self.m and self.m.id in PagesEmbed.instances:
            del PagesEmbed.instances[self.m.id]
        embed = self.embed_copy()
        embed.set_footer(text=self.get_req_text()+' | '+get_text('timed_out'))
        await self.m.clear_reactions()
        await self.m.edit(embed=embed)


    @classmethod
    async def destroy_old(cls):
        to_destroy = []
        for instance in cls.instances.values():
            if (now() - instance.time).total_seconds() > 60 * 5:
                to_destroy.append(instance)
        for instance in to_destroy:
            await instance.self_destruct()

    @classmethod
    async def on_reaction_add(cls, reaction, user):
        if str(reaction) in EMOJIS and reaction.message.id in PagesEmbed.instances:
            instance = PagesEmbed.instances[reaction.message.id]
            if user.id == instance.ctx.author.id:
                instance.time = now()
                page = instance.page
                if str(reaction) == FIRST_EMOJI:
                    page = 1
                elif str(reaction) == PREV_EMOJI:
                    page -= 1
                elif str(reaction) == NEXT_EMOJI:
                    page += 1
                elif str(reaction) == LAST_EMOJI:
                    page = instance.pages
                elif str(reaction) == STOP_EMOJI:
                    page = None

                if page == None:
                    await instance.self_destruct()
                else:
                    await instance.m.edit(embed=instance.make_page(page))
            await reaction.remove(user)