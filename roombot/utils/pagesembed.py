import discord
from roombot.utils.constants import FIRST_EMOJI, PREV_EMOJI, NEXT_EMOJI, LAST_EMOJI, STOP_EMOJI
from roombot.utils.functions import now, clamp
from roombot.database.settings import Settings
from math import ceil
from abc import ABCMeta, abstractmethod

PAGES_EMOJIS = [FIRST_EMOJI, PREV_EMOJI, NEXT_EMOJI, LAST_EMOJI, STOP_EMOJI]

class PagesEmbed(metaclass=ABCMeta):
    instances = {}

    @abstractmethod
    def __init__(self, ctx, total, per):
        self.ctx = ctx
        self.settings = Settings.get_for(ctx.guild.id)
        self.per = per
        self.pages = ceil(total/per)
        self.page = 1
        self.m = None
        self.time = now()

    @abstractmethod
    def make_page(self):
        pass

    @abstractmethod
    def make_timed_out_page(self):
        pass

    def get_text(self, key):
        return self.settings.get_text(key)

    def get_req_text(self):
        return self.get_text('request')+': '+self.ctx.author.display_name

    def get_page(self, i):
        i = clamp(i, 1, self.pages)
        self.page = i
        page_text = self.get_text('page').format(i, self.pages)
        embed = self.make_page()
        embed.set_footer(text=self.get_req_text()+' | '+page_text)
        return embed


    async def send(self):
        self.m = await self.ctx.send(embed=self.get_page(1))
        for emoji in PAGES_EMOJIS:
            await self.m.add_reaction(emoji)
        PagesEmbed.instances[self.m.id] = self

    async def self_destruct(self):
        if self.m and self.m.id in PagesEmbed.instances:
            del PagesEmbed.instances[self.m.id]
        embed = self.make_timed_out_page()
        embed.set_footer(text=self.get_req_text()+' | '+self.get_text('timed_out'))
        await self.m.clear_reactions()
        await self.m.edit(embed=embed)


    @classmethod
    async def delete_old(cls):
        to_destroy = []
        for instance in cls.instances.values():
            if (now() - instance.time).total_seconds() > 60 * 5:
                to_destroy.append(instance)
        for instance in to_destroy:
            await instance.self_destruct()

    @classmethod
    async def on_reaction_add(cls, reaction, user):
        if str(reaction) in PAGES_EMOJIS and reaction.message.id in PagesEmbed.instances:
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
                    await instance.m.edit(embed=instance.get_page(page))
            await reaction.remove(user)
        
class FieldPagesEmbed(PagesEmbed):

    def __init__(self, ctx, embed, fields_per_page=3):
        super().__init__(ctx, len(embed.fields), fields_per_page)
        self.embed = embed

    def make_page(self):
        i = self.page
        embed = self.embed_copy()
        for j in range(self.per):
            k = (i-1) * self.per + j
            if k < len(self.embed.fields):
                field = self.embed.fields[k]
                embed.add_field(inline=field.inline, name=field.name, value=field.value)
        return embed

    def make_timed_out_page(self):
        return self.embed_copy()

    def embed_copy(self):
        return discord.Embed(**self.embed.to_dict())


class EmbedPagesEmbed(PagesEmbed):

    def __init__(self, ctx, embeds, timed_out_embed):
        super().__init__(ctx, len(embeds), 1)
        self.embeds = embeds
        self.timed_out_embed = timed_out_embed

    def make_page(self):
        return self.embeds[self.page-1]

    def make_timed_out_page(self):
        return self.timed_out_embed