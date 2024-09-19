# modules/devoirs/add.py

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import logging
from modules.data_manager import data, save_data

# Constantes
TIMEZONE = 'Europe/Paris'
REMINDER_ROLE_NAME = 'reminder'

def setup_add(bot):
    @bot.command()
    async def add(ctx, date: str, heure: str, *, titre: str):
        """Ajouter un nouveau devoir pour le serveur actuel."""
        guild_id = str(ctx.guild.id)
        # Initialiser les données du serveur si elles n'existent pas
        if guild_id not in data['guilds']:
            data['guilds'][guild_id] = {'devoirs': []}

        guild_data = data['guilds'][guild_id]

        try:
            tz = pytz.timezone(TIMEZONE)
            due_date = datetime.strptime(f"{date} {heure}", '%d-%m-%Y %H:%M:%S')
            due_date = tz.localize(due_date)
        except ValueError:
            await ctx.send("Format de date ou d'heure invalide. Utilisez JJ-MM-AAAA HH:MM:SS.")
            return

        # Retirer les guillemets autour du titre s'ils existent
        titre = titre.strip('"\'')
        
        # Vérifier les doublons
        for devoir in guild_data['devoirs']:
            if devoir['date'] == date and devoir['heure'] == heure and devoir['titre'].lower() == titre.lower():
                await ctx.send(f"Le devoir '{titre}' pour le {date} à {heure} existe déjà.")
                return

        # Créer l'événement Discord
        event_id = None
        try:
            event = await ctx.guild.create_scheduled_event(
                name=titre,
                start_time=due_date,
                end_time=due_date + timedelta(hours=1),
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location="Discord"
            )
            event_id = event.id
        except Exception as e:
            await ctx.send(f"Erreur lors de la création de l'événement Discord : {e}")
            logging.error(f"Erreur lors de la création de l'événement Discord : {e}")

        # Ajouter le devoir
        devoir_data = {
            'date': date,
            'heure': heure,
            'titre': titre,  # Titre sans guillemets
            'guild_id': ctx.guild.id,
            'reminders_sent': []
        }

        if event_id:
            devoir_data['event_id'] = event_id

        guild_data['devoirs'].append(devoir_data)
        save_data(data)

        # Ajouter une réaction de coche au message de commande
        await ctx.message.add_reaction('✅')
