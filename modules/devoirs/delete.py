# modules/devoirs/delete.py

import discord
from discord.ext import commands
import logging
from modules.data_manager import data, save_data

def setup_delete(bot):
    @bot.command()
    async def delete(ctx, *, titre: str):
        """Supprimer un devoir existant en fonction de son titre."""
        guild_id = str(ctx.guild.id)
        if guild_id not in data['guilds']:
            await ctx.send("Aucun devoir n'est actuellement enregistré pour ce serveur.")
            return

        guild_data = data['guilds'][guild_id]
        # Retirer les guillemets autour du titre s'ils existent
        titre = titre.strip('"\'')
        for devoir in guild_data['devoirs']:
            if devoir['titre'].lower() == titre.lower():
                guild_data['devoirs'].remove(devoir)
                save_data(data)
                await ctx.message.add_reaction('✅')

                # Supprimer l'événement Discord associé si existant
                guild = bot.get_guild(devoir['guild_id'])
                if guild and 'event_id' in devoir:
                    try:
                        event = await guild.fetch_scheduled_event(devoir['event_id'])
                        await event.delete()
                    except Exception as e:
                        await ctx.send(f"Erreur lors de la suppression de l'événement associé : {e}")
                        logging.error(f"Erreur lors de la suppression de l'événement Discord : {e}")
                return
        await ctx.send(f"Aucun devoir trouvé avec le titre '{titre}'.")
