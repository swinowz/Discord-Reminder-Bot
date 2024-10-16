# modules/data_manager.py

import json
import os
from modules.usage import init_env, get_env

init_env()
DATA_FILE = get_env('DATA_FILE')
if DATA_FILE is None:
    raise Exception("Veuillez spécifier DATA_FILE dans .env")
else:
    DATA_FILE = str(DATA_FILE)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                # On s'assure que la clé 'guilds' existe
                if 'guilds' not in data:
                    data = {'guilds': {}}
                else:
                    # Pour chaque serveur, on s'assure que 'devoirs' et 'settings' existent
                    for guild_id, guild_data in data['guilds'].items():
                        if 'devoirs' not in guild_data:
                            guild_data['devoirs'] = []
                        if 'settings' not in guild_data:
                            guild_data['settings'] = {}
                        else:
                            if 'reminder_channel_id' not in guild_data['settings']:
                                guild_data['settings']['reminder_channel_id'] = None
                            if 'reminder_intervals' not in guild_data['settings']:
                                guild_data['settings']['reminder_intervals'] = []
                return data
            except json.JSONDecodeError:
                # Si le fichier JSON est invalide, on initialise une structure vide
                return {'guilds': {}}
    # Si le fichier n'existe pas, on initialise une structure vide
    return {'guilds': {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Objet de données partagé
data = load_data()
