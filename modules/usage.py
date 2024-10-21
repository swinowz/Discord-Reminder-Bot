# modules/usage.py

import discord
from discord.ext import commands
import logging
from os import getenv
from dotenv import load_dotenv

def setup_usage(bot):
    @bot.command()
    async def usage(ctx):
        """Affiche les instructions d'utilisation."""
        embed = discord.Embed(
            title="Liste des commandes disponibles",
            color=0x00ff00
        )
        embed.add_field(
            name="!add",
            value=(
                "Ajouter un nouveau devoir.\n"
                "Format : `!add <date> <heure> <titre> <rôle>`\n"
                "Exemple : `!add 20-09-2024 08:00:00 \"Cours de mathématiques\" dev`"
            ),
            inline=False
        )
        embed.add_field(
            name="!delete",
            value=(
                "Supprimer un devoir existant en fonction de son titre.\n"
                "Format : `!delete <titre>`\n"
                "Exemple : `!delete \"Cours de mathématiques\"`\n"
                "Les guillemets autour du titre sont optionnels."
            ),
            inline=False
        )
        embed.add_field(
            name="!list",
            value="Lister tous les devoirs enregistrés.",
            inline=False
        )
        embed.add_field(
            name="!settings",
            value=(
                "Ouvre le menu des paramètres pour configurer le bot.\n"
                "Options disponibles :\n"
                "- Définir le canal des rappels\n"
                "- Configurer les intervalles de rappels\n"
                "- Supprimer des devoirs\n"
                "Seuls les administrateurs peuvent utiliser cette commande."
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @bot.event
    async def on_command_error(ctx, error):
        """Gère les erreurs globalement."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignorer les commandes inconnues
        elif isinstance(error, commands.CheckFailure):
            return  # Les échecs de vérification sont déjà gérés
        else:
            await ctx.send(f"Une erreur s'est produite : {error}")
            logging.error(f"Une erreur s'est produite : {error}")

def init_env():
    load_dotenv()

def get_env(key):
    return getenv(key)
