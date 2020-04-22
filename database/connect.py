import dataset
import os
import env

db = dataset.connect(os.getenv('DATABASE_URL'))
rooms_db = db.get_table('rooms', primary_id='role_id', primary_type=db.types.bigint)
settings_db = db.get_table('settings', primary_id='guild_id', primary_type=db.types.bigint)