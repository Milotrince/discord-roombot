import discord
import json
import os

print('ROOMBOT')

current_dir = os.path.dirname(__file__)
with open(os.path.join(current_dir, 'config.json')) as config_file:  
    config = json.load(config_file)


class Bot(discord.Client):

    async def on_ready(self):
        print('{0} is online!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user or not message.content.startswith(config['prefix']):
            return

        args = message.content.split(' ')
        
        if args[1] == 'hi':
            await message.channel.send('Hello!')

bot = Bot()
bot.run(config['token'])