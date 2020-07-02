import dataset
from os import getenv

class RoomBotDatabase:
    instance = None

    class __RoomBotDatabase:
        def __init__(self, connection_string): 
            db = dataset.connect(connection_string)
            self.rooms = db.get_table('rooms', primary_id='role_id', primary_type=db.types.bigint)
            self.settings = db.get_table('settings', primary_id='guild_id', primary_type=db.types.bigint)
            self.invites = db.get_table('invites')

    def __init__(self, connection_string=getenv('DATABASE_URL')):
        if not RoomBotDatabase.instance:
            RoomBotDatabase.instance = RoomBotDatabase.__RoomBotDatabase(connection_string)

    def __getattr__(self, name):
        return getattr(self.instance, name)