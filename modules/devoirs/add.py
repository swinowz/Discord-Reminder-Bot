# modules/add.py

import discord
from discord.ext import commands
from modules.data_manager import data, save_data
import logging
from datetime import datetime, timedelta
import pytz

def setup_add_commands(bot):
    @bot.command()
    async def add(ctx, date, time, title, role_name):
        """Ajouter un nouveau devoir."""
        tz = pytz.timezone('Europe/Paris')
        guild_id = str(ctx.guild.id)
        guild = ctx.guild
        guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})
        try:
            due_date = datetime.strptime(f"{date} {time}", '%d-%m-%Y %H:%M:%S')
            due_date = tz.localize(due_date)
        except ValueError:
            await ctx.send("Format de date ou d'heure invalide. Utilisez le format `DD-MM-YYYY` pour la date et `HH:MM:SS` pour l'heure.")
            return

        # Vérifier si le rôle existe
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            await ctx.send(f"Le rôle `{role_name}` n'existe pas sur ce serveur.")
            return

        # Créer l'événement Discord
        try:
            event = await guild.create_scheduled_event(
                name=title,
                start_time=due_date,
                end_time=due_date + timedelta(hours=1),
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location="Discord"
            )
            event_id = event.id
        except Exception as e:
            logging.error(f"Erreur lors de la création de l'événement Discord : {e}")
            event_id = None

        # Ajouter le devoir aux données
        devoir_data = {
            'date': date,
            'heure': time,
            'titre': title,
            'guild_id': ctx.guild.id,
            'role_to_ping': role.id,
            'reminders_sent': [],
            'event_id': event_id
        }
        guild_data['devoirs'].append(devoir_data)
        save_data(data)

        await ctx.message.add_reaction('✅')

    @bot.command()
    async def delete(ctx, *, title):
        """Supprimer un devoir existant."""
        guild_id = str(ctx.guild.id)
        guild = ctx.guild
        guild_data = data['guilds'].get(guild_id, {'devoirs': [], 'settings': {}})

        devoir_to_delete = None
        for devoir in guild_data['devoirs']:
            if devoir['titre'].lower() == title.lower():
                devoir_to_delete = devoir
                break

        if devoir_to_delete:
            # Supprimer l'événement Discord associé si existant
            if 'event_id' in devoir_to_delete:
                try:
                    event = await guild.fetch_scheduled_event(devoir_to_delete['event_id'])
                    await event.delete()
                except Exception as e:
                    logging.error(f"Erreur lors de la suppression de l'événement Discord : {e}")

            guild_data['devoirs'].remove(devoir_to_delete)
            save_data(data)
            await ctx.message.add_reaction('✅')
        else:
            await ctx.send(f"Aucun devoir trouvé avec le titre : {title}")

    @bot.command()
    async def list(ctx):
        """Lister tous les devoirs enregistrés."""
        guild_id = str(ctx.guild.id)
        guild_data = data['guilds'].get(guild_id, {'devoirs': [], 'settings': {}})
        devoirs = guild_data['devoirs']

        if not devoirs:
            await ctx.send("Aucun devoir n'est enregistré.")
            return

        embed = discord.Embed(title="Liste des devoirs", color=0x00ff00)
        for devoir in devoirs:
            embed.add_field(
                name=devoir['titre'],
                value=f"Date : {devoir['date']} {devoir['heure']}\nRôle à pinger : <@&{devoir['role_to_ping']}>",
                inline=False
            )
        await ctx.send(embed=embed)
