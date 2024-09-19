# modules/events.py

import discord
from discord.ext import tasks
from datetime import datetime
import pytz
import math
import logging
from modules.data_manager import data, save_data

# Constantes
TIMEZONE = 'Europe/Paris'
REMINDER_ROLE_NAME = 'reminder'

bot = None  # Variable globale pour le bot

def setup_events(b):
    global bot
    bot = b
    # Pas besoin de démarrer la boucle ici

@tasks.loop(minutes=3)
async def reminder_loop():
    """Boucle qui vérifie les devoirs à rappeler toutes les 3 minutes."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    for guild_id, guild_data in data['guilds'].items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue

        role = discord.utils.get(guild.roles, name=REMINDER_ROLE_NAME)
        if not role:
            continue

        # Choisir un canal approprié
        channel = guild.system_channel or (guild.text_channels and guild.text_channels[0])
        if not channel:
            continue

        for devoir in guild_data['devoirs'][:]:
            try:
                due_date = tz.localize(datetime.strptime(f"{devoir['date']} {devoir['heure']}", '%d-%m-%Y %H:%M:%S'))
            except ValueError as e:
                logging.error(f"Format de date invalide pour le devoir '{devoir['titre']}': {e}")
                continue

            time_diff = due_date - now
            total_seconds = time_diff.total_seconds()
            days_until_due = math.ceil(total_seconds / 86400)
            hours_until_due = (time_diff.seconds // 3600) % 24
            minutes_until_due = (time_diff.seconds % 3600) // 60

            if 'reminders_sent' not in devoir:
                devoir['reminders_sent'] = []

            if total_seconds <= 0:
                # Le devoir est en retard
                embed = discord.Embed(title=f"Le devoir '{devoir['titre']}' est en retard", color=0xff0000)
                embed.description = (f"Ce devoir était à rendre le {devoir['date']} à {devoir['heure']}.\n"
                                     "Il a été supprimé de la liste.")
                await channel.send(embed=embed)
                guild_data['devoirs'].remove(devoir)
                save_data(data)

                # Supprimer l'événement Discord associé si existant
                if 'event_id' in devoir:
                    try:
                        event = await guild.fetch_scheduled_event(devoir['event_id'])
                        await event.delete()
                    except Exception as e:
                        logging.error(f"Erreur lors de la suppression de l'événement Discord : {e}")
            else:
                embed = discord.Embed(title=f"Rappel : '{devoir['titre']}'", color=0x00ff00)
                sent_reminders = devoir['reminders_sent']
                # Envoyer des rappels à des intervalles spécifiques
                if days_until_due in [14, 7, 3, 1] and days_until_due not in sent_reminders:
                    embed.description = f"Il reste {days_until_due} jour(s) avant l'échéance."
                    await channel.send(content=role.mention, embed=embed)
                    devoir['reminders_sent'].append(days_until_due)
                    save_data(data)
                elif days_until_due == 0 and hours_until_due > 0 and 0 not in sent_reminders:
                    embed.description = (f"Il reste {hours_until_due} heure(s) et "
                                         f"{minutes_until_due} minute(s) avant l'échéance.")
                    await channel.send(content=role.mention, embed=embed)
                    devoir['reminders_sent'].append(0)
                    save_data(data)

@reminder_loop.before_loop
async def before_reminder_loop():
    await bot.wait_until_ready()
