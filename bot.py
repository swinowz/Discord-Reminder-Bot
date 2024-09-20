# bot.py
import discord
from discord.ext import commands
import logging
from modules.devoirs import setup_devoirs_commands
from modules.events import setup_events, reminder_loop
from modules.utility import setup_utility, init_env, get_env

init_env()

TOKEN = get_env('TOKEN')
PREFIX = '!'

# Configuration des logs
logging.basicConfig(level=logging.INFO)

# Configuration des intents nécessaires
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # Nécessaire pour créer des événements
intents.guild_scheduled_events = True  # Activer l'intent pour les événements planifiés

# Initialisation du bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Configuration des modules
setup_devoirs_commands(bot)
setup_utility(bot)
setup_events(bot)

@bot.event
async def on_ready():
    logging.info(f'Connecté en tant que {bot.user}')
    if not reminder_loop.is_running():
        reminder_loop.start()
        logging.info('La boucle de rappel a été démarrée.')

bot.run(TOKEN)
