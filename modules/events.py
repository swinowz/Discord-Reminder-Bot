# modules/events.py

import discord
from discord.ext import tasks
from datetime import datetime, timedelta
import pytz
import logging
from modules.data_manager import data, save_data
import math

# Constantes
TIMEZONE = 'Europe/Paris'

bot = None  # Variable globale pour le bot

def setup_events(b):
    global bot
    bot = b
    # La boucle de rappel sera démarrée dans bot.py

def get_time_left(due_date, tz):
    """Calculate and format the remaining time for a reminder, ensuring days round up when > 24 hours."""
    now = datetime.now(tz)
    time_left = due_date - now
    total_seconds = int(time_left.total_seconds())
    if total_seconds < 0:
        return "Échéance dépassée."

    # Convertir en jours, heures, minutes
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    # If there are any hours remaining with more than 24 hours in total, round up days
    if hours > 0 or minutes > 0:
        days += 1

    # Afficher uniquement les jours si plus de 24 heures, sinon afficher heures/minutes restants
    if days > 1:
        return f"Il reste {days} jour(s) avant l'échéance."
    else:
        parts = []
        if hours > 0:
            parts.append(f"{hours} heure(s)")
        if minutes > 0:
            parts.append(f"{minutes} minute(s)")
        return "Il reste " + ", ".join(parts) + " avant l'échéance."

@tasks.loop(minutes=1)
async def reminder_loop():
    """Boucle qui vérifie les rappels de devoirs toutes les minutes."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    for guild_id, guild_data in data['guilds'].items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue

        # Récupérer le canal configuré pour les rappels
        channel_id = guild_data.get('settings', {}).get('reminder_channel_id')
        channel = guild.get_channel(channel_id) if channel_id else guild.system_channel or (guild.text_channels and guild.text_channels[0])
        if not channel:
            continue

        # Récupérer les intervalles de rappels configurés pour ce serveur
        reminder_intervals = guild_data.get('settings', {}).get('reminder_intervals', [14 * 86400, 7 * 86400, 3 * 86400, 1 * 86400, 0])
        reminder_intervals.sort(reverse=True)  # Trier par ordre décroissant

        for devoir in guild_data['devoirs'][:]:
            try:
                due_date = tz.localize(datetime.strptime(f"{devoir['date']} {devoir['heure']}", '%d-%m-%Y %H:%M:%S'))
            except ValueError as e:
                logging.error(f"Format de date invalide pour le devoir '{devoir['titre']}': {e}")
                continue

            time_diff = due_date - now
            total_seconds = time_diff.total_seconds()

            if 'reminders_sent' not in devoir:
                devoir['reminders_sent'] = []

            if total_seconds <= 0:
                # Le devoir est en retard
                embed = discord.Embed(title=f"Le devoir '{devoir['titre']}' est en retard", color=0xff0000)
                embed.description = (f"Ce devoir devait être rendu le {devoir['date']} à {devoir['heure']}.\n"
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
                sent_reminders = devoir['reminders_sent']
                role_id = devoir.get('role_to_ping')
                role = guild.get_role(role_id)

                # Envoyer les rappels en fonction des intervalles de rappel
                for interval in reminder_intervals:
                    if interval in sent_reminders:
                        continue  # Passer les intervalles pour lesquels les rappels ont déjà été envoyés

                    reminder_time = due_date - timedelta(seconds=interval)

                    # Définir une marge d'erreur de 5 minutes
                    if now >= reminder_time and (now - reminder_time).total_seconds() <= 300:
                        # Il est temps d'envoyer le rappel
                        embed = discord.Embed(title=f"Rappel : '{devoir['titre']}'", color=0x00ff00)
                        embed.description = get_time_left(due_date, tz)

                        if role:
                            await channel.send(content=role.mention, embed=embed)
                        else:
                            await channel.send(embed=embed)

                        devoir['reminders_sent'].append(interval)
                        save_data(data)
                        break  # Éviter d'envoyer plusieurs rappels en même temps

@reminder_loop.before_loop
async def before_reminder_loop():
    await bot.wait_until_ready()
    logging.info("La boucle de rappel est prête et démarrera sous peu.")
