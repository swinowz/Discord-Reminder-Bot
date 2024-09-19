# modules/devoirs/list.py

import discord
from discord.ext import commands
from modules.data_manager import data, save_data

def setup_list(bot):
    @bot.command(name='list')
    async def list(ctx):
        """Lister tous les devoirs du serveur actuel."""
        guild_id = str(ctx.guild.id)
        if guild_id not in data['guilds'] or not data['guilds'][guild_id]['devoirs']:
            await ctx.send("Aucun devoir n'est actuellement enregistré pour ce serveur.")
            return

        guild_data = data['guilds'][guild_id]
        message = "**Liste des devoirs :**\n"
        for devoir in guild_data['devoirs']:
            message += (f"- **{devoir['titre']}** "
                        f"(Pour le {devoir['date']} à {devoir['heure']})\n")
        await ctx.send(message)
