import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os
import logging
import pytz

TOKEN = ''
PREFIX = '!'

logging.basicConfig(level=logging.DEBUG)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

def charger_devoirs():
    logging.debug("Chargement des devoirs depuis le fichier JSON.")
    if os.path.exists('devoirs.json'):
        with open('devoirs.json', 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.error("Erreur de décodage JSON.")
                return {'devoirs': [], 'channel_id': None}
    logging.debug("Fichier JSON non trouvé, création d'une nouvelle structure de données.")
    return {'devoirs': [], 'channel_id': None}

def sauvegarder_devoirs(data):
    logging.debug("Sauvegarde des devoirs dans le fichier JSON.")
    with open('devoirs.json', 'w') as f:
        json.dump(data, f, indent=4)

async def mention_reminder():
    logging.debug("Entering reminder mention loop.")
    channel_id = 1283358461282746379  # Channel ID should be an integer
    channel = bot.get_channel(channel_id)
    
    if channel:
        guild = channel.guild
        role = discord.utils.get(guild.roles, name="reminder")
        if role:
            await channel.send(f'{role.mention}, c\'est l\'heure des rappels !')
        else:
            print('Role named "reminder" not found')
    else:
        print('Channel not found')

data = charger_devoirs()

@bot.event
async def on_ready():
    logging.info(f'Le bot s\'est connecté en tant que {bot.user}')
    if not reminder_loop.is_running():
        reminder_loop.start()


@bot.command()
async def ajouter_devoir(ctx, date: str = None, heure: str = None, type_devoir: str = None, titre: str = None, *, description: str = None):
    if not all([date, heure, type_devoir, titre, description]):
        embed = discord.Embed(title="Usage des commandes", color=0x00ff00)
        embed.add_field(name="Commande Daily", value="Ajoute un rappel quotidien à 00:00 chaque jour.\nExemple : !ajouter_devoir 29-08-2024 18:00:00 daily \"Titre du Devoir\" \"Description du devoir\"", inline=False)
        embed.add_field(name="Commande Reminder", value="Ajoute un rappel aux intervalles spécifiques (7 jours, 3 jours, 1 jour et moins de 24 heures avant l'échéance).\nExemple : !ajouter_devoir 29-08-2024 18:00:00 reminder \"Titre du Devoir\" \"Description du devoir\"", inline=False)
        await ctx.send(embed=embed)
        return

    logging.debug(f"Commande ajouter_devoir reçue avec la date : {date}, l'heure : {heure}, le type : {type_devoir}, le titre : {titre} et la description : {description}")
    try:
        tz = pytz.timezone('Europe/Paris')
        due_date = datetime.strptime(date + ' ' + heure, '%d-%m-%Y %H:%M:%S')
        due_date = tz.localize(due_date)
    except ValueError:
        await ctx.send("Format de date ou d'heure invalide. Utilisez JJ-MM-AAAA HH:MM:SS.")
        logging.warning("Format de date ou d'heure invalide reçu.")
        return
    
    channel_id = ctx.channel.id
    data['channel_id'] = channel_id

    # Check for duplicate entry
    for devoir in data['devoirs']:
        if devoir['date'] == date and devoir['heure'] == heure and devoir['description'] == description:
            await ctx.send(f"Le devoir '{description}' pour le {date} à {heure} existe déjà.")
            logging.info(f"Devoir en double détecté : {description} pour le {date} à {heure}")
            return

    # Add the devoir entry to JSON
    data['devoirs'].append({'date': date, 'heure': heure, 'type': type_devoir.lower(), 'titre': titre, 'description': description})
    sauvegarder_devoirs(data)
    await ctx.send(f'Devoir ajouté : {titre} pour le {date} à {heure}')
    logging.info(f"Devoir ajouté : {titre} pour le {date} à {heure}")

    # Creating a Discord event for both 'daily' and 'reminder' types
    if type_devoir.lower() in ['daily', 'reminder']:
        try:
            event = await ctx.guild.create_scheduled_event(
                name=titre,
                description=description,
                start_time=due_date,
                end_time=due_date + timedelta(hours=1),
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location="CCIDISCORD"
            )

            # Save the event ID in JSON for future reference
            for devoir in data['devoirs']:
                if devoir['date'] == date and devoir['heure'] == heure:
                    devoir['event_id'] = event.id
                    break
            sauvegarder_devoirs(data)

            await ctx.send(f"Événement Discord ajouté pour le devoir '{titre}' à {date} {heure}.")
            logging.info(f"Événement Discord ajouté pour le devoir '{titre}' à {date} {heure}.")
        except Exception as e:
            await ctx.send(f"Erreur lors de la création de l'événement : {e}")
            logging.error(f"Erreur lors de la création de l'événement : {e}")

@bot.command()
async def list(ctx):
    logging.debug("Commande list reçue")
    if not data['devoirs']:
        await ctx.send("Aucun devoir n'est actuellement enregistré.")
        return

    message = "**Liste des devoirs :**\n"
    for devoir in data['devoirs']:
        message += f"- {devoir['titre']} : {devoir['description']} (Date : {devoir['date']} à {devoir['heure']}, Type : {devoir['type']})\n"
    await ctx.send(message)
    logging.info("Liste des devoirs envoyée")

@bot.event
async def on_command_error(ctx, error):
    logging.error(f"Une erreur s'est produite lors de l'exécution de la commande : {error}")
    await ctx.send(f"Une erreur s'est produite : {error}")

reminder_sent_today = False


@tasks.loop(minutes=1)
async def reminder_loop():
    global reminder_sent_today
    timezone = pytz.timezone('Europe/Paris')
    now = datetime.now(timezone)
    logging.info(f"Il est {now.hour}:{now.minute}")

    if (now.hour > 23 and now.minute >= 58) or (now.hour == 0 and now.minute <= 3):
        await mention_reminder() 
        if not reminder_sent_today:
            logging.debug("Exécution de la boucle de rappel.")
            devoirs_a_supprimer = []
            for devoir in data['devoirs']:
                due_date_naive = datetime.strptime(devoir['date'] + ' ' + devoir['heure'], '%d-%m-%Y %H:%M:%S')
                due_date = timezone.localize(due_date_naive)

                time_diff = due_date - now
                days_until_due = time_diff.days
                hours_until_due = int(time_diff.total_seconds() // 3600)
                minutes_until_due = int((time_diff.total_seconds() % 3600) // 60)

                embed = discord.Embed(title=f"Rappel pour '{devoir['titre']}'", color=0x00ff00)

                if due_date < now:
                    embed.title = f" Le devoir '{devoir['titre']}' est en retard"
                    embed.description = f"Ce devoir était à rendre depuis le {devoir['date']} à {devoir['heure']}.\nLe devoir a été retiré car la date est passée."
                    await envoyer_rappel(embed)
                    devoirs_a_supprimer.append(devoir)
                    logging.info(f"Devoir retiré : {devoir['titre']} pour le {devoir['date']} à {devoir['heure']}")

                elif devoir['type'] == 'daily' and days_until_due >= 0:
                    if days_until_due == 0 and time_diff.total_seconds() > 0:
                        embed.description = f"Il reste {hours_until_due} heures et {minutes_until_due} minutes avant l'échéance."
                        await envoyer_rappel(embed)
                    else:
                        embed.description = f"Il reste {days_until_due} jour(s) avant l'échéance."
                        await envoyer_rappel(embed)
                elif devoir['type'] == 'reminder':
                    if days_until_due == 7:
                        embed.description = f"Il reste une semaine avant l'échéance."
                        await envoyer_rappel(embed)
                    elif days_until_due == 3:
                        embed.description = f"Il reste trois jours avant l'échéance."
                        await envoyer_rappel(embed)
                    elif days_until_due == 1:
                        embed.description = f"Il reste un jour avant l'échéance."
                        await envoyer_rappel(embed)
                    elif days_until_due == 0 and time_diff.total_seconds() > 0:
                        embed.description = f"Il reste {hours_until_due} heures et {minutes_until_due} minutes avant l'échéance."
                        await envoyer_rappel(embed)

            for devoir in devoirs_a_supprimer:
                data['devoirs'].remove(devoir)
            sauvegarder_devoirs(data)

            reminder_sent_today = True
    else:
        reminder_sent_today = False

async def envoyer_rappel(embed):
    channel_id = data.get('channel_id')
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)
        else:
            logging.warning(f"Impossible de trouver le canal avec l'ID : {channel_id}")

bot.run(TOKEN)
