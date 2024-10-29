# modules/settings.py

import discord
from discord.ext import commands
from modules.data_manager import data, save_data
import logging
from datetime import datetime, timedelta
import pytz

def setup_settings(bot):
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def settings(ctx):
        """Ouvre le menu des paramètres."""

        # Supprimer le message de commande de l'utilisateur
        try:
            await ctx.message.delete()
        except Exception as e:
            logging.error(f"Impossible de supprimer le message de commande : {e}")

        # Création du message embed
        embed = discord.Embed(
            title="Paramètres du Bot",
            description="Choisissez une option pour modifier les paramètres.",
            color=0x00ff00
        )

        # Création des boutons
        class SettingsView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=10)  # Réduction du timeout à 10 secondes
                self.ctx = ctx
                self.message = None

            async def on_timeout(self):
                # Désactiver les boutons lorsque le temps est écoulé
                for child in self.children:
                    child.disabled = True
                if self.message:
                    await self.message.edit(view=self)
                    await self.message.delete()  # Supprimer le message immédiatement

            @discord.ui.button(label="Définir le canal des rappels", style=discord.ButtonStyle.primary)
            async def set_reminder_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Créer un menu déroulant pour les canaux
                options = [
                    discord.SelectOption(
                        label=channel.name,
                        value=str(channel.id)
                    )
                    for channel in self.ctx.guild.text_channels
                ]

                select = ChannelSelect(options, self.ctx)
                view = discord.ui.View()
                view.add_item(select)

                await interaction.response.send_message(
                    "Veuillez sélectionner le canal pour les rappels.",
                    view=view
                )
                # Supprimer le message après un délai
                message = await interaction.original_response()
                await message.delete(delay=15)

            @discord.ui.button(label="Configurer les intervalles de rappels", style=discord.ButtonStyle.secondary)
            async def set_reminder_intervals(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Créer une vue pour les intervalles de rappels
                intervals_view = IntervalsView(self.ctx)
                await interaction.response.send_message(
                    "Veuillez sélectionner les intervalles de rappels souhaités.",
                    view=intervals_view
                )
                # Supprimer le message après un délai
                message = await interaction.original_response()
                await message.delete(delay=15)

            #@discord.ui.button(label="Génération de Débogage", style=discord.ButtonStyle.success)
            #async def debug_generation(self, interaction: discord.Interaction, button: discord.ui.Button):
            #    await interaction.response.defer()
            #    await self.generate_debug_homeworks()
            #    message = await interaction.followup.send("Les devoirs de débogage ont été générés.")
            #    await message.delete(delay=5)

            @discord.ui.button(label="Supprimer des devoirs", style=discord.ButtonStyle.danger)
            async def delete_homeworks(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Demander le type de suppression
                delete_view = DeleteOptionsView(self.ctx)
                await interaction.response.send_message(
                    "Choisissez une option de suppression :",
                    view=delete_view
                )
                # Supprimer le message après un délai
                message = await interaction.original_response()
                await message.delete(delay=15)

        # Classe pour la sélection des canaux
        class ChannelSelect(discord.ui.Select):
            def __init__(self, options, ctx):
                super().__init__(placeholder="Sélectionnez un canal...", options=options)
                self.ctx = ctx

            async def callback(self, interaction: discord.Interaction):
                channel_id = int(self.values[0])
                channel = self.ctx.guild.get_channel(channel_id)
                guild_id = str(self.ctx.guild.id)
                guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})
                guild_data['settings']['reminder_channel_id'] = channel_id
                save_data(data)
                message = await interaction.response.send_message(f"Le canal des rappels a été défini sur {channel.mention}.")
                await message.delete(delay=5)
                self.view.stop()

        # Classe pour la configuration des intervalles
        class IntervalsView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=10)
                self.ctx = ctx
                self.selected_intervals = []
                self.interval_options = [
                    ('10 jours', 10 * 86400),
                    ('7 jours', 7 * 86400),
                    ('5 jours', 5 * 86400),
                    ('3 jours', 3 * 86400),
                    ('2 jours', 2 * 86400),
                    ('1 jour', 1 * 86400),
                    ('18 heures', 18 * 3600),
                    ('10 heures', 10 * 3600),
                    ('3 heures', 3 * 3600),
                ]
                options = [
                    discord.SelectOption(label=label, value=str(seconds))
                    for label, seconds in self.interval_options
                ]
                self.add_item(IntervalsSelect(options, self))

            async def on_timeout(self):
                # Désactiver les éléments lorsque le temps est écoulé
                for child in self.children:
                    if isinstance(child, discord.ui.Button) or isinstance(child, discord.ui.Select):
                        child.disabled = True

        class IntervalsSelect(discord.ui.Select):
            def __init__(self, options, parent_view):
                super().__init__(placeholder="Sélectionnez les intervalles...", options=options, min_values=1, max_values=len(options))
                self.parent_view = parent_view

            async def callback(self, interaction: discord.Interaction):
                self.parent_view.selected_intervals = [int(value) for value in self.values]
                guild_id = str(interaction.guild.id)
                guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})
                guild_data['settings']['reminder_intervals'] = self.parent_view.selected_intervals
                save_data(data)
                message = await interaction.response.send_message("Les intervalles de rappels ont été mis à jour.")
                await message.delete(delay=5)
                self.parent_view.stop()

        # Classe pour la sélection des options de suppression
        class DeleteOptionsView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=10)
                self.ctx = ctx

            async def on_timeout(self):
                # Désactiver les boutons lorsque le temps est écoulé
                for child in self.children:
                    child.disabled = True

            @discord.ui.button(label="Supprimer tous les devoirs", style=discord.ButtonStyle.danger)
            async def delete_all(self, interaction: discord.Interaction, button: discord.ui.Button):
                confirm_view = ConfirmView(self.ctx)
                await interaction.response.send_message(
                    "⚠️ **ATTENTION** ⚠️\n\nÊtes-vous sûr de vouloir supprimer **tous les devoirs** et les événements associés ? Cette action est irréversible.",
                    view=confirm_view
                )
                # Supprimer le message après un délai
                message = await interaction.original_response()
                await message.delete(delay=15)
                self.stop()

            @discord.ui.button(label="Annuler", style=discord.ButtonStyle.grey)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                message = await interaction.response.send_message("Opération annulée.")
                await message.delete(delay=5)
                self.stop()

            async def delete_homeworks(self, debug_only=False):
                guild_id = str(self.ctx.guild.id)
                guild = self.ctx.guild
                guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})

                devoirs_to_delete = []
                for devoir in guild_data['devoirs']:
                    if debug_only and not devoir.get('debug', False):
                        continue
                    devoirs_to_delete.append(devoir)

                # Supprimer les événements Discord associés
                for devoir in devoirs_to_delete:
                    if 'event_id' in devoir:
                        try:
                            event = await guild.fetch_scheduled_event(devoir['event_id'])
                            await event.delete()
                        except Exception as e:
                            logging.error(f"Erreur lors de la suppression de l'événement Discord : {e}")

                # Retirer les devoirs supprimés de la liste
                guild_data['devoirs'] = [d for d in guild_data['devoirs'] if d not in devoirs_to_delete]
                save_data(data)

        # Classe pour la confirmation de suppression
        class ConfirmView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=10)
                self.ctx = ctx

            async def on_timeout(self):
                # Désactiver les boutons lorsque le temps est écoulé
                for child in self.children:
                    child.disabled = True

            @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Déférer la réponse de l'interaction
                await interaction.response.defer()

                guild_id = str(self.ctx.guild.id)
                guild = self.ctx.guild
                guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})

                # Supprimer les événements Discord associés
                for devoir in guild_data['devoirs'][:]:  # Utiliser une copie de la liste
                    if 'event_id' in devoir:
                        try:
                            event = await guild.fetch_scheduled_event(devoir['event_id'])
                            await event.delete()
                        except Exception as e:
                            logging.error(f"Erreur lors de la suppression de l'événement Discord : {e}")

                    guild_data['devoirs'].remove(devoir)  # Supprimer le devoir de la liste

                save_data(data)

                message = await interaction.followup.send("Tous les devoirs et les événements associés ont été supprimés.")
                await message.delete(delay=5)
                self.stop()

            @discord.ui.button(label="Annuler", style=discord.ButtonStyle.grey)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                message = await interaction.response.send_message("Suppression annulée.")
                await message.delete(delay=5)
                self.stop()

        # Envoyer le message du menu des paramètres
        view = SettingsView(ctx)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    # Gestion des erreurs pour permissions manquantes
    @settings.error
    async def settings_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            message = await ctx.send("Vous devez être administrateur pour utiliser cette commande.")
            await message.delete(delay=5)
            # Supprimer le message de l'utilisateur après avoir informé de l'erreur
            try:
                await ctx.message.delete(delay=5)
            except Exception as e:
                logging.error(f"Impossible de supprimer le message de commande : {e}")
        else:
            raise error
