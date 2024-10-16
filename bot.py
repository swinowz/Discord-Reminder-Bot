# bot.py

import discord
from discord.ext import commands
import logging
from modules.devoirs import setup_add_commands
from modules.events import setup_events, reminder_loop
from modules.usage import setup_usage, init_env, get_env
from modules.settings import setup_settings
from modules.data_manager import data
from discord.ext.commands import CheckFailure

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
setup_add_commands(bot)
setup_usage(bot)
setup_events(bot)
setup_settings(bot)

# Définition du check global
@bot.check
async def check_reminder_intervals(ctx):
    # Commandes autorisées même si les intervalles ne sont pas définis
    allowed_commands = ['settings', 'usage', 'help']

    # Si la commande est dans allowed_commands, on la permet
    if ctx.command.name in allowed_commands:
        return True

    # Vérifier si c'est une commande de message (éviter les DM)
    if ctx.guild is None:
        await ctx.send("Cette commande ne peut être utilisée en message privé.")
        return False

    # Obtenir l'ID du serveur
    guild_id = str(ctx.guild.id)

    # Obtenir les données du serveur
    guild_data = data['guilds'].get(guild_id, {})

    # Vérifier si les intervalles de rappels sont définis
    reminder_intervals = guild_data.get('settings', {}).get('reminder_intervals', None)

    if not reminder_intervals:
        # Intervalles non définis, bloquer la commande
        await ctx.send("Les intervalles de rappels ne sont pas encore configurés. Veuillez utiliser `!settings` pour les configurer avant d'utiliser les autres commandes.")
        return False

    # Les intervalles sont définis, permettre la commande
    return True

@bot.event
async def on_ready():
    logging.info(f'Connecté en tant que {bot.user}')
    if not reminder_loop.is_running():
        reminder_loop.start()
        logging.info('La boucle de rappel a été démarrée.')

bot.run(TOKEN)
