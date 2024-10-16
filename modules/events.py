# modules/events.py

import discord
from discord.ext import tasks
from datetime import datetime, timedelta
import pytz
import logging
from modules.data_manager import data, save_data

# Constantes
TIMEZONE = 'Europe/Paris'

bot = None  # Variable globale pour le bot

def setup_events(b):
    global bot
    bot = b
    # La boucle de rappel sera démarrée dans bot.py

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
        if channel_id:
            channel = guild.get_channel(channel_id)
        else:
            # Si aucun canal n'est défini, utiliser le canal système ou le premier canal texte disponible
            channel = guild.system_channel or (guild.text_channels and guild.text_channels[0])

        if not channel:
            continue

        # Récupérer les intervalles de rappels configurés pour ce serveur
        reminder_intervals = guild_data.get('settings', {}).get('reminder_intervals', [])
        if not reminder_intervals:
            # Si aucun intervalle n'est défini, utiliser les intervalles par défaut
            reminder_intervals = [14 * 86400, 7 * 86400, 3 * 86400, 1 * 86400, 0]

        # Trier les intervalles par ordre décroissant
        reminder_intervals.sort(reverse=True)

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

                # Récupérer le rôle à mentionner
                role_id = devoir.get('role_to_ping')
                role = guild.get_role(role_id)

                # Pour chaque intervalle, vérifier s'il est temps d'envoyer le rappel
                for interval in reminder_intervals:
                    if interval in sent_reminders:
                        continue  # Passer les intervalles pour lesquels les rappels ont déjà été envoyés

                    reminder_time = due_date - timedelta(seconds=interval)

                    # Définir une marge d'erreur de 5 minutes
                    if now >= reminder_time and (now - reminder_time).total_seconds() <= 300:
                        # Il est temps d'envoyer le rappel
                        time_remaining = due_date - now

                        days_left = time_remaining.days
                        hours_left = time_remaining.seconds // 3600
                        minutes_left = (time_remaining.seconds % 3600) // 60

                        if days_left > 0:
                            embed = discord.Embed(title=f"Rappel : '{devoir['titre']}'", color=0x00ff00)
                            embed.description = f"Il reste {days_left} jour(s) avant l'échéance."
                        elif hours_left > 0 or minutes_left > 0:
                            embed = discord.Embed(title=f"Rappel : '{devoir['titre']}'", color=0x00ff00)
                            embed.description = f"Il reste {hours_left} heure(s) et {minutes_left} minute(s) avant l'échéance."
                        else:
                            embed = discord.Embed(title=f"Rappel : '{devoir['titre']}'", color=0xffa500)
                            embed.description = "L'échéance est très proche !"

                        if role:
                            await channel.send(content=role.mention, embed=embed)
                        else:
                            await channel.send(embed=embed)

                        devoir['reminders_sent'].append(interval)
                        save_data(data)
                        break  # Éviter d'envoyer plusieurs rappels en même temps

