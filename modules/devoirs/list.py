# modules/devoirs/list.py

import discord
from discord.ext import commands
from modules.data_manager import data

def setup_list(bot):
    @bot.command(name='list')
    async def list_devoirs(ctx):
        """Lister tous les devoirs du serveur actuel."""
        guild_id = str(ctx.guild.id)
        if guild_id not in data['guilds'] or not data['guilds'][guild_id]['devoirs']:
            await ctx.send("Aucun devoir n'est actuellement enregistré pour ce serveur.")
            return

        guild_data = data['guilds'][guild_id]
        message = "**Liste des devoirs :**\n"
        for devoir in guild_data['devoirs']:
            role_id = devoir.get('role_to_ping')
            role = ctx.guild.get_role(role_id)
            role_name = role.name if role else 'Aucun rôle'
            message += (f"- **{devoir['titre']}** "
                        f"(Pour le {devoir['date']} à {devoir['heure']}) "
                        f"- Rôle : {role_name}\n")
        await ctx.send(message)
