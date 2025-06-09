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

# ==================== UTILS ====================
def parse_time_str(time_str: str) -> str:
    """Return a HH:MM:SS string applying smart defaults"""
    if not time_str:
        return "00:00:01"
    parts = time_str.split(":")
    if len(parts) == 1:
        return f"{parts[0].zfill(2)}:00:00"
    if len(parts) == 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
    if len(parts) == 3:
        return ":".join(p.zfill(2) for p in parts[:3])
    raise ValueError("Invalid time format")


def check_command_permission(ctx: SlashContext, command: str) -> bool:
    """Check if the user has permission for the command"""
    global_data = load_data(DATA_FILE)
    guild_id = str(ctx.guild_id)
    guild_data = global_data["guilds"].setdefault(guild_id, {"devoirs": [], "settings": {}})
    perms = guild_data["settings"].get("command_permissions", {}).get(command)
    if perms is None:
        return True
    member_perms = getattr(ctx.author, "permissions", 0)
    if hasattr(member_perms, "value"):
        member_perms = member_perms.value
    return (member_perms & perms) == perms

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
        logger.debug("================================================================")
        logger.debug("reminder_loop: 🔄 Starting iteration...")  # DEBUG START
        global_data = load_data(DATA_FILE)

        for guild_id, guild_data in global_data["guilds"].items():
            now = datetime.now(tz)
            devoirs = guild_data["devoirs"]

            for devoir in devoirs[:]:  # Iterate over a copy to allow removal
                due_date = tz.localize(datetime.strptime(f"{devoir['date']} {devoir['heure']}", "%d/%m/%Y %H:%M:%S"))
                channel_id = devoir.get("channel_id")

                if not channel_id:
                    logger.warning(f"Missing channel_id for '{devoir['titre']}', skipping reminder.")
                    continue  # Skip if no channel assigned

                if now >= due_date:
                    # Send overdue reminder
                    embed_dict = {
                        "title": f"🚨 Le devoir '{devoir['titre']}' est en retard 🚨",
                        "color": 0xFF0000,
                        "description": f"Ce devoir devait être rendu le {devoir['date']} à {devoir['heure']}."
                    }
                    if devoir.get("description"):
                        embed_dict.setdefault("fields", []).append({
                            "name": "Description",
                            "value": devoir["description"],
                            "inline": False
                        })

                    await send_msg(TOKEN, int(channel_id), content="", embed=embed_dict)
                    
                    # Remove from list & delete event
                    devoirs.remove(devoir)

                    if "event_id" in devoir:
                        logger.debug(f"reminder_loop: 🗑️ Deleting event {devoir['event_id']}...")  # DEBUG DELETE EVENT
                        await delete_scheduled(TOKEN, int(guild_id), devoir["event_id"])
                    
                    save_data(global_data, DATA_FILE)

                else:
                    # Check reminders before the due date
                    reminder_intervals = guild_data.get("settings", {}).get("reminder_intervals", [86400, 3600, 600])
                    for interval in sorted(reminder_intervals, reverse=True):
                        if interval in devoir["reminders_sent"]:
                            continue  # Skip if already sent

                        reminder_time = due_date - timedelta(seconds=interval)
                        marge = 300  # Allow 5 min margin

                        if now >= reminder_time and (now - reminder_time).total_seconds() <= marge:
                            embed_dict = {
                                "title": f"📢 Rappel : '{devoir['titre']}' 📢",
                                "color": 0x00FF00,
                                "description": f"Ce devoir est prévu pour le {devoir['date']} à {devoir['heure']}."
                            }
                            if devoir.get("description"):
                                embed_dict.setdefault("fields", []).append({
                                    "name": "Description",
                                    "value": devoir["description"],
                                    "inline": False
                                })


                            role_id = devoir.get("role_to_ping")
                            mention_str = f"<@&{role_id}>" if role_id else ""


                            await send_msg(TOKEN, int(channel_id), content=mention_str, embed=embed_dict)


                            devoir["reminders_sent"].append(interval)
                            save_data(global_data, DATA_FILE)
                            break  # Stop checking once a reminder is sent

        await asyncio.sleep(60)  # Check every minute




# ==================== COMMANDES ====================
#----------------------------#
###--------  Add  ---------###
#----------------------------#
@interactions.slash_command(name="add", description="Ajouter un devoir et spécifier un canal de rappel", scopes=[guild_id_int])
@interactions.slash_option(name="date", description="Date (DD/MM/YYYY)", required=True, opt_type=OptionType.STRING)
@interactions.slash_option(name="titre", description="Titre du devoir", required=True, opt_type=OptionType.STRING)
@interactions.slash_option(name="role", description="Nom du rôle à pinger", required=True, opt_type=OptionType.STRING)
@interactions.slash_option(name="channel", description="Canal pour le rappel", required=True, opt_type=OptionType.STRING)
@interactions.slash_option(name="heure", description="Heure (HH:MM[:SS])", required=False, opt_type=OptionType.STRING)
@interactions.slash_option(name="description", description="Description du devoir", required=False, opt_type=OptionType.STRING)

async def add_command(ctx: SlashContext, date: str, titre: str, role: str, channel: str, heure: str | None, description: str | None):
    if not check_command_permission(ctx, "add"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    guild_data = global_data["guilds"].setdefault(guild_id_str, {"devoirs": [], "settings": {}})
    tz = pytz.timezone(TIMEZONE)

    heure = parse_time_str(heure or "")
    try:
        due_date = tz.localize(datetime.strptime(f"{date} {heure}", "%d/%m/%Y %H:%M:%S"))
        if due_date < datetime.now(tz):
            return await ctx.send("🚫 La date et l'heure sont déjà passées. 🚫", ephemeral=True)
    except ValueError:
        return await ctx.send("Format invalide. Utilisez `DD/MM/YYYY HH:MM[:SS]`.", ephemeral=True)

    channels_json = await get_channels(TOKEN, ctx.guild_id)
    channel_id = next((c["id"] for c in channels_json if c["name"] == channel and c["type"] == 0), None)

    if not channel_id:
        return await ctx.send(f"🚫 Canal `{channel}` introuvable ou non textuel 🚫", ephemeral=True)

    # Fetch role ID
    roles_json = await get_roles(TOKEN, ctx.guild_id)
    role_id = next((r["id"] for r in roles_json if r["name"] == role), None)
    if not role_id:
        return await ctx.send(f"🚫 Rôle `{role}` introuvable 🚫", ephemeral=True)

    # Create the scheduled event
    start_iso = due_date.isoformat()
    end_iso = (due_date + timedelta(hours=1)).isoformat()

    try:
        event_data = await create_scheduled(TOKEN, ctx.guild_id, titre, start_iso, end_iso)
        event_id = event_data.get("id")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'événement: {e}")
        event_id = None

    devoir = {
        "date": date,
        "heure": heure,
        "titre": titre,
        "description": description,
        "channel_id": channel_id,
        "role_to_ping": role_id,
        "event_id": event_id,
        "reminders_sent": []
    }

    guild_data["devoirs"].append(devoir)
    save_data(global_data, DATA_FILE)

    await ctx.send("✅ Devoir ajouté avec succès et événement créé ✅", ephemeral=True)

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
    if not check_command_permission(ctx, "delete"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
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
    if not check_command_permission(ctx, "list"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    guild_data = global_data["guilds"].get(guild_id_str, {"devoirs": [], "settings": {}})
    devoirs = guild_data["devoirs"]
    if not devoirs:
        return await ctx.send("Aucun devoir n'est enregistré pour ce serveur.", ephemeral=True)
    lines = []
    for d in devoirs:
        desc = f" - {d['description']}" if d.get('description') else ""
        lines.append(f"- **{d['titre']}**{desc} (Date: {d['date']} {d['heure']}, Rôle: <@&{d['role_to_ping']}>)")
    await ctx.send("Devoirs enregistrés:\n" + "\n".join(lines), ephemeral=True)


#----------------------------#
###--- Setup intervals ----###
#----------------------------#
@interactions.slash_command(name="setupintervals",description="Définir les intervalles de rappel",scopes=[guild_id_int],
                            default_member_permissions= 8192) 
# 8 = Admin et 8192 = manage_messages <- en gros ceux qui ont au moins une des perms peuvent faire la cmd 

async def setupintervals_command(ctx: SlashContext):
    if not check_command_permission(ctx, "setupintervals"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
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
                            default_member_permissions=8192)
async def export_command(ctx: SlashContext):
    if not check_command_permission(ctx, "export"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
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

#----------------------------#
###-------- Import --------###
#----------------------------#
@interactions.slash_command(name="import", description="Importer des rappels depuis un JSON", scopes=[guild_id_int], default_member_permissions=8192)
@interactions.slash_option(name="json_file", description="Fichier JSON", required=True, opt_type=OptionType.ATTACHMENT)
async def import_command(ctx: SlashContext, json_file):
    if not check_command_permission(ctx, "import"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
    if not str(json_file.filename).endswith(".json"):
        return await ctx.send("Le fichier doit être en JSON", ephemeral=True)
    content = await json_file.read()
    try:
        imported = json.loads(content.decode())
    except Exception:
        return await ctx.send("JSON invalide", ephemeral=True)
    global_data = load_data(DATA_FILE)
    guild_id_str = str(ctx.guild_id)
    global_data["guilds"][guild_id_str] = imported
    save_data(global_data, DATA_FILE)
    await ctx.send("Données importées", ephemeral=True)

#----------------------------#
###------ Set Perms --------###
#----------------------------#
@interactions.slash_command(name="setperm", description="Définir la permission d'une commande", scopes=[guild_id_int], default_member_permissions=8192)
@interactions.slash_option(name="commande", description="Nom de la commande", required=True, opt_type=OptionType.STRING)
@interactions.slash_option(name="bits", description="Bits de permission", required=True, opt_type=OptionType.INTEGER)
async def setperm_command(ctx: SlashContext, commande: str, bits: int):
    if not check_command_permission(ctx, "setperm"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
    global_data = load_data(DATA_FILE)
    guild_id = str(ctx.guild_id)
    guild_data = global_data["guilds"].setdefault(guild_id, {"devoirs": [], "settings": {}})
    perms = guild_data["settings"].setdefault("command_permissions", {})
    perms[commande] = bits
    save_data(global_data, DATA_FILE)
    await ctx.send(f"Permission pour {commande} enregistrée", ephemeral=True)

#----------------------------#
###----- Mass Delete -------###
#----------------------------#
@interactions.slash_command(name="massdelete", description="Supprimer en masse par préfixe", scopes=[guild_id_int], default_member_permissions=8192)
@interactions.slash_option(name="prefix", description="Préfixe du titre", required=True, opt_type=OptionType.STRING)
async def massdelete_command(ctx: SlashContext, prefix: str):
    if not check_command_permission(ctx, "massdelete"):
        return await ctx.send("🚫 Permission insuffisante 🚫", ephemeral=True)
    global_data = load_data(DATA_FILE)
    guild_id = str(ctx.guild_id)
    guild_data = global_data["guilds"].get(guild_id, {"devoirs": [], "settings": {}})
    devoirs = guild_data.get("devoirs", [])
    to_remove = [d for d in list(devoirs) if d["titre"].startswith(prefix)]
    if not to_remove:
        return await ctx.send("Aucun devoir ne correspond", ephemeral=True)
    for d in to_remove:
        if "event_id" in d:
            await delete_scheduled(TOKEN, ctx.guild_id, d["event_id"])
        devoirs.remove(d)
    save_data(global_data, DATA_FILE)
    await ctx.send(f"{len(to_remove)} devoirs supprimés", ephemeral=True)


# ==================== MAIN ====================
@listen()#logs

async def on_ready():
    logger.info("Bot prêt !")
    asyncio.create_task(reminder_loop())

if __name__ == "__main__":
    asyncio.run(bot.start())


    
    
    
