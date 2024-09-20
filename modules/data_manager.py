# modules/data_manager.py

import json
import os
from modules.utility import get_env

DATA_FILE = get_env('DATA_FILE')
if DATA_FILE == None:
    raise Exception("Please specify DATA_FILE in .env")
else:
    DATA_FILE = str(DATA_FILE)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                # Vérifiez si la clé 'guilds' existe
                if 'guilds' not in data:
                    # Si la structure est ancienne (sans 'guilds'), initialisez avec une structure vide
                    data = {'guilds': {}}
                return data
            except json.JSONDecodeError:
                # Initialisez avec une structure vide si le JSON est invalide
                return {'guilds': {}}
    # Initialisez avec une structure vide si le fichier n'existe pas
    return {'guilds': {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Objet de données partagé
data = load_data()