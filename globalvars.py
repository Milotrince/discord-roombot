import dataset
import json

# Get database
db = dataset.connect('sqlite:///database.db')
rooms_db = db.get_table('rooms', primary_id='role_id')
settings_db = db.get_table('settings', primary_id='guild_id')

# Get json file of strings
with open('config/strings.json', 'r', encoding='utf-8') as strings_file:  
    strings = json.load(strings_file)