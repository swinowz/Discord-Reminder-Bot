import os
import json
import logging
import asyncio
from datetime import datetime, timedelta

import aiohttp
import pytz
import interactions
from interactions import (
    Intents,
    listen,
    SlashContext,
    OptionType,
    StringSelectMenu,
    StringSelectOption,
    ComponentContext
)
from dotenv import load_dotenv

# ==================== LOGGING & ENV ====================
#Le projet est sur un scope restreint (  GUILD ID ) et pas en global 
#pcq en global les commandes mettent jusqu'à 1h pour s'actualiser

#Activation des logs 
logging.basicConfig()
logger = logging.getLogger("MyLogger")
logger.setLevel(logging.DEBUG)

#Récup des variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = os.getenv("DATA_FILE", "homeworks.json")
GUILD_ID = os.getenv("GUILD_ID")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")

if not TOKEN:
    raise ValueError("Variable DISCORD_TOKEN manquante dans le fichier .env")
if not GUILD_ID:
    raise ValueError("Variable GUILD_ID in .env")

guild_id_int = int(GUILD_ID)

# ==================== JSON MANAGER ====================
def load_data(data_file: str) -> dict:
    if os.path.exists(data_file):
        try:
            with open(data_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    if "guilds" not in data:
        data["guilds"] = {}
    return data

def save_data(data: dict, data_file: str):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

# ==================== RAW HTTP HELPERS ====================
# Fonctions qui font des appels sur l'API discord (récupérer des rôles, créer des événements etc )

async def get_channels(bot_token: str, guild_id: int) -> list:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    headers = {"Authorization": f"Bot {bot_token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

async def get_roles(bot_token: str, guild_id: int) -> list:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
    headers = {"Authorization": f"Bot {bot_token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

async def send_msg(bot_token: str, channel_id: int, content: str = "", embed: dict = None):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    payload = {"content": content}
    if embed:
        payload["embeds"] = [embed]

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status not in [200, 201]:
                txt = await resp.text()
                logger.warning(f"send_msg failed: {resp.status} {txt}")

async def create_scheduled(bot_token: str, guild_id: int, name: str,
                                     start_time: str, end_time: str) -> dict:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/scheduled-events"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "privacy_level": 2,
        "scheduled_start_time": start_time,
        "scheduled_end_time": end_time,
        "entity_type": 3,
        "entity_metadata": {"location": "Discord"},
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            return await resp.json()

async def delete_scheduled(bot_token: str, guild_id: int, event_id: str):
    url = f"https://discord.com/api/v10/guilds/{guild_id}/scheduled-events/{event_id}"
    headers = {"Authorization": f"Bot {bot_token}"}
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as resp:
            if resp.status not in [200, 204]:
                txt = await resp.text()
                logger.warning(f"delete_scheduled failed: {resp.status} {txt}")


# ==================== BOT  ====================
bot = interactions.Client(
    token=TOKEN,
    intents=Intents.DEFAULT | Intents.MESSAGE_CONTENT,
    logger=logger,
    sync_commands=True,
    asyncio_debug=True
)

# ==================== REMINDER LOOP ====================
def time_left(due_date: datetime, now: datetime) -> str:
    diff = due_date - now
    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        return ""
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    if days > 1:
        return "" #logger.info(f"Il reste {days} jour(s) avant l'échéance.")
    parts = []
    if hours > 0:
        parts.append(f"{hours} heure(s)")
    if minutes > 0:
        parts.append(f"{minutes} minute(s)")
    return "" # logger.info("Il reste " + ", ".join(parts) + " avant l'échéance.")

async def reminder_loop():
    """
    Runs every 60 seconds, checking for overdue or reminder intervals.
    More logging added to debug issues.
    """
    tz = pytz.timezone(TIMEZONE)

    while True:
        logger.debug("reminder_loop: 🔄 Starting iteration...")  # DEBUG START
        global_data = load_data(DATA_FILE)

        for guild_id, guild_data in global_data["guilds"].items():
            logger.debug(f"reminder_loop: 🏠 Checking guild {guild_id}...")  # DEBUG GUILD CHECK

            settings = guild_data.get("settings", {})
            channel_id = settings.get("reminder_channel_id")
            if not channel_id:
                logger.debug(f"reminder_loop: ❌ No reminder_channel_id set for guild {guild_id}")  # DEBUG NO CHANNEL
                continue

            # Fetch intervals or use default
            reminder_intervals = settings.get("reminder_intervals", [14*86400, 7*86400, 3*86400, 1*86400, 0])
            reminder_intervals.sort(reverse=True)

            devoirs = guild_data["devoirs"]
            now = datetime.now(tz)
            logger.debug(f"reminder_loop: 📋 Found {len(devoirs)} devoir(s) for guild {guild_id}.")  # DEBUG DEVOIRS FOUND

            # Process each homework
            for devoir in devoirs[:]:
                logger.debug(f"reminder_loop: 📌 Checking devoir: {devoir.get('titre')}")  # DEBUG CHECKING TASK

                try:
                    due_str = f"{devoir['date']} {devoir['heure']}"
                    due_date = tz.localize(datetime.strptime(due_str, "%d-%m-%Y %H:%M:%S"))
                    logger.debug(f"reminder_loop: 🕒 Parsed due_date={due_date}, now={now}")  # DEBUG TIME PARSE

                except ValueError as e:
                    logger.error(f"reminder_loop: ⚠️ Format de date invalide pour '{devoir['titre']}' : {e}")
                    continue

                if "reminders_sent" not in devoir:
                    devoir["reminders_sent"] = []

                time_diff = (due_date - now).total_seconds()
                logger.debug(f"reminder_loop: ⏳ time_diff={time_diff}s for '{devoir['titre']}'")  # DEBUG TIME LEFT

                if time_diff <= 0:
                    # Overdue => remove from list, send overdue message
                    logger.debug(f"reminder_loop: 🚨 Devoir '{devoir['titre']}' is overdue!")  # DEBUG OVERDUE

                    embed_dict = {
                        "title": f"⚠️ Le devoir '{devoir['titre']}' est en retard",
                        "color": 0xFF0000,
                        "description": f"📅 Ce devoir devait être rendu le {devoir['date']} à {devoir['heure']}.\n❌ Il a été supprimé de la liste."
                    }

                    await send_msg(TOKEN, int(channel_id), content="", embed=embed_dict)
                    devoirs.remove(devoir)

                    if "event_id" in devoir:
                        logger.debug(f"reminder_loop: 🗑️ Deleting event {devoir['event_id']}...")  # DEBUG DELETE EVENT
                        await delete_scheduled(TOKEN, int(guild_id), devoir["event_id"])
                    
                    save_data(global_data, DATA_FILE)
                else:
                    # Not overdue => check reminder intervals
                    logger.debug(f"reminder_loop: ✅ Devoir '{devoir['titre']}' is NOT overdue. Checking intervals...")  # DEBUG INTERVAL CHECK

                    for interval in reminder_intervals:
                        if interval in devoir["reminders_sent"]:
                            logger.debug(f"reminder_loop: ⏭️ Interval {interval}s already sent for '{devoir['titre']}'")  # DEBUG SKIP SENT
                            continue

                        reminder_time = due_date - timedelta(seconds=interval)
                        margin = 300  # 5 min

                        if now >= reminder_time and (now - reminder_time).total_seconds() <= margin:
                            logger.debug(f"reminder_loop: 🚀 Sending reminder for interval {interval}s on '{devoir['titre']}'")  # DEBUG SENDING REMINDER

                            # Get time left message
                            left_str = time_left(due_date, now)
                            logger.debug(f"reminder_loop: 🕒 Time left: {left_str}")  # DEBUG TIME LEFT

                            # Build embed
                            embed_dict = {
                                "title": "📌 Rappel de devoir",
                                "color": 0x00FF00,
                                "description": f"**Il reste {left_str} avant le rendu suivant :**\n➤ **{devoir['titre']}**"
                            }

                            role_id = devoir.get("role_to_ping")
                            mention_str = f"<@&{role_id}>" if role_id else ""

                            await send_msg(TOKEN, int(channel_id), content=mention_str, embed=embed_dict)

                            devoir["reminders_sent"].append(interval)
                            save_data(global_data, DATA_FILE)
                            break  # Avoid sending multiple reminders at once

        logger.debug("reminder_loop: ⏳ Sleeping 60s before next iteration.")  # DEBUG SLEEP
        await asyncio.sleep(60)


# ==================== COMMANDES ====================
#----------------------------#
###--------  Add  ---------###
#----------------------------#
@interactions.slash_command(name="add",    description="Ajouter un devoir et créer un événement planifié",   scopes=[guild_id_int])
@interactions.slash_option( name="date",   description="Date (DD-MM-YYYY)",   required=True, opt_type=OptionType.STRING)
@interactions.slash_option( name="heure",  description="Heure (HH:MM:SS)",    required=True, opt_type=OptionType.STRING)
@interactions.slash_option( name="titre",  description="Titre du devoir",     required=True, opt_type=OptionType.STRING)
@interactions.slash_option( name="role",   description="Nom du rôle à pinger",required=True, opt_type=OptionType.STRING)

async def add_command(ctx: SlashContext, date: str, heure: str, titre: str, role: str):
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    guild_data = global_data["guilds"].setdefault(guild_id_str, {"devoirs": [], "settings": {}})
    tz = pytz.timezone(TIMEZONE)

    try:
        # Convertir la date et l'heure en un objet datetime
        due_date = datetime.strptime(f"{date} {heure}", "%d-%m-%Y %H:%M:%S")
        due_date = tz.localize(due_date)

        # verif si la date est dans le passé
        now = datetime.now(tz)
        if due_date < now:
            return await ctx.send("🚫 La date et l'heure fournies sont déjà dans le passé. Veuillez entrer une date future 🚫", ephemeral=True)

    except ValueError:
        return await ctx.send("Format invalide. Utilisez `DD-MM-YYYY HH:MM:SS`.", ephemeral=True)

    # verif si le rôle existe
    roles_json = await get_roles(TOKEN, ctx.guild_id)
    role_id = next((r["id"] for r in roles_json if r["name"] == role), None)
    if not role_id:
        return await ctx.send(f"🚫 Rôle `{role}` introuvable 🚫", ephemeral=True)

    # Créer l'événement programmé
    start_iso = due_date.isoformat()
    end_iso = (due_date + timedelta(hours=1)).isoformat()
    try:
        event_data = await create_scheduled(TOKEN, ctx.guild_id, titre, start_iso, end_iso)
        event_id = event_data.get("id")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'événement: {e}")
        event_id = None

    # Ajouter le devoir dans les données
    devoir = {
        "date": date,
        "heure": heure,
        "titre": titre,
        "guild_id": ctx.guild_id,
        "role_to_ping": role_id,
        "reminders_sent": [],
        "event_id": event_id
    }
    guild_data["devoirs"].append(devoir)
    save_data(global_data, DATA_FILE)

    await ctx.send("✅ Devoir ajouté avec succès ✅", ephemeral=True)


#----------------------------#
###-------- Delete --------###
#----------------------------#
@interactions.slash_command(
    name="delete",
    description="Supprimer un devoir par titre",
    scopes=[guild_id_int]
)
@interactions.slash_option(
    name="title",
    description="Titre du devoir à supprimer",
    required=True,
    opt_type=OptionType.STRING
)
async def delete_command(ctx: SlashContext, title: str):
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    guild_data = global_data["guilds"].get(guild_id_str, {"devoirs": [], "settings": {}})
    devoirs = guild_data["devoirs"]
    if not devoirs:
        return await ctx.send("Aucun devoir n'est enregistré pour ce serveur.", ephemeral=True)
    devoir_to_delete = next((d for d in devoirs if d["titre"].lower() == title.lower()), None)
    if not devoir_to_delete:
        return await ctx.send(f"Aucun devoir trouvé avec le titre: {title}", ephemeral=True)
    if "event_id" in devoir_to_delete:
        await delete_scheduled(TOKEN, ctx.guild_id, devoir_to_delete["event_id"])
    devoirs.remove(devoir_to_delete)
    save_data(global_data, DATA_FILE)
    await ctx.send(f"Devoir '{title}' supprimé avec succès ✅", ephemeral=True)

#----------------------------#
###--------  List  --------###
#----------------------------#
@interactions.slash_command(
    name="list",
    description="Lister tous les devoirs",
    scopes=[guild_id_int]
)
async def list_command(ctx: SlashContext):
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    guild_data = global_data["guilds"].get(guild_id_str, {"devoirs": [], "settings": {}})
    devoirs = guild_data["devoirs"]
    if not devoirs:
        return await ctx.send("Aucun devoir n'est enregistré pour ce serveur.", ephemeral=True)
    lines = [f"- **{d['titre']}** (Date: {d['date']} {d['heure']}, Rôle: <@&{d['role_to_ping']}>)" for d in devoirs]
    await ctx.send("Devoirs enregistrés:\n" + "\n".join(lines), ephemeral=True)

#----------------------------#
###---- Setup Channels ----###
#----------------------------#
@interactions.slash_command(
    name="setupchannel",
    description="Définir le canal de rappel en spécifiant son nom",
    scopes=[guild_id_int],
    default_member_permissions=8192  # Manage Messages permission
)
@interactions.slash_option(
    name="channel_name",
    description="Nom du canal (ex: devoirs)",
    required=True,
    opt_type=OptionType.STRING
)
async def setupchannel_command(ctx: SlashContext, channel_name: str):
    """
    Commande qui permet de définir le canal des rappels en entrant son nom.
    Seuls les utilisateurs avec la permission "Gérer les messages" ou "Administrateur" peuvent l'utiliser.
    """
    raw_channels = await get_channels(TOKEN, ctx.guild_id)
    text_channels = [ch for ch in raw_channels if ch["type"] == 0]

    # trouver le channel
    matching_channel = next((ch for ch in text_channels if ch["name"].lower() == channel_name.lower()), None)

    if not matching_channel:
        return await ctx.send(f"❌ Aucun canal trouvé avec le nom `{channel_name}`.", ephemeral=True)

    # save l'ID du chann dans le json
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    guild_data = global_data["guilds"].setdefault(guild_id_str, {"devoirs": [], "settings": {}})
    guild_data["settings"]["reminder_channel_id"] = matching_channel["id"]
    save_data(global_data, DATA_FILE)

    await ctx.send(f"✅ Le canal des rappels est maintenant <#{matching_channel['id']}>", ephemeral=True)
    
#----------------------------#
###--- Setup intervals ----###
#----------------------------#
@interactions.slash_command(name="setupintervals",description="Définir les intervalles de rappel",scopes=[guild_id_int],
                            default_member_permissions= 8192) 
# 8 = Admin et 8192 = manage_messages <- en gros ceux qui ont au moins une des perms peuvent faire la cmd 

async def setupintervals_command(ctx: SlashContext):
    """"
    Commande pour définir les intervalles de rappel (besoin des perms "Gérer les messages" ou "Administrateur")
    """
    interval_data = [("10 jours", 10*86400),("7 jours", 7*86400)  ,("5 jours", 5*86400)  ,("3 jours", 3*86400),  ("2 jours", 2*86400),
                     ("1 jour", 86400)     ,("18 heures", 18*3600),("10 heures", 10*3600),("3 heures", 3*3600),  ("1 heure", 3600)]

    select_options = [StringSelectOption(label=label, value=str(secs)) for label, secs in interval_data]
    menu = StringSelectMenu(
        *select_options,
        custom_id="select_intervals",
        placeholder="Choisissez un ou plusieurs intervalles",
        min_values=1,
        max_values=len(select_options)
    )

    await ctx.send(
        "Sélectionnez vos intervalles de rappels :",
        components=[interactions.ActionRow(menu)],
        ephemeral=True
    )

@interactions.component_callback("select_intervals")
async def on_select_intervals_callback(ctx: ComponentContext):
    selected = [int(v) for v in ctx.values]
    global_data = load_data(DATA_FILE)
    guild_id = str(ctx.guild_id)
    guild_data = global_data["guilds"].setdefault(guild_id, {"devoirs": [], "settings": {}})
    guild_data["settings"]["reminder_intervals"] = selected
    save_data(global_data, DATA_FILE)
    await ctx.send(f"Intervalles enregistrés: {selected}", ephemeral=True)

#----------------------------#
###-------- Backup --------###
#----------------------------#
@interactions.slash_command(name="export",description="Exporter une sauvegarde des devoirs",scopes=[guild_id_int],
                            default_member_permissions=8)
async def export_command(ctx: SlashContext):
    """Créer une sauvegarde des devoirs enregistrés sur le serveur et envoi la backup en DM"""
    guild_id_str = str(ctx.guild_id)  #
    global_data = load_data(DATA_FILE)  # chargement du fichier json entier
    guild_data = global_data["guilds"].get(guild_id_str, None)  # récup les données json du serveur

    if not guild_data:
        return await ctx.send("Aucune donnée pour ce serveur.", ephemeral=True)

    # préparation du fichier temporaire avec les données du serveur uniquement
    backup = f"backup_{guild_id_str}.json"
    json_data = json.dumps(guild_data, indent=4)
    with open(backup, "w") as backup_file:
        backup_file.write(json_data)
    await ctx.send("✅ Backup envoyée en DM ✅", ephemeral=True)

    # envoi DM
    try:
        user = ctx.author
        dm_channel = await user.fetch_dm()
        await dm_channel.send(
            content=f"Fichier de backup pour les données du serveur **{ctx.guild.name}**.",
            files=[interactions.File(backup)]
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du DM : {e}")
        await ctx.send("Erreur : Impossible d'envoyer le fichier en DM.", ephemeral=True)

    # Clean up the temporary file
    os.remove(backup)


# ==================== MAIN ====================
@listen()#logs

async def on_ready():
    logger.info("Bot prêt !")
    asyncio.create_task(reminder_loop())

if __name__ == "__main__":
    asyncio.run(bot.start())


    
    
    
