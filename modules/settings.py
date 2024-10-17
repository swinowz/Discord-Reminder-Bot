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
                self.ctx = ctx  # Stocker le contexte pour une utilisation ultérieure
                self.message = None  # Stocker le message du menu pour pouvoir le gérer

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
                    view=view,
                    delete_after=15  # Le message sera supprimé après 15 secondes
                )

            @discord.ui.button(label="Configurer les intervalles de rappels", style=discord.ButtonStyle.secondary)
            async def set_reminder_intervals(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Créer une vue pour les intervalles de rappels
                intervals_view = IntervalsView(self.ctx)
                await interaction.response.send_message(
                    "Veuillez sélectionner les intervalles de rappels souhaités.",
                    view=intervals_view,
                    delete_after=15  # Le message sera supprimé après 15 secondes
                )

            @discord.ui.button(label="Génération de Débogage", style=discord.ButtonStyle.success)
            async def debug_generation(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Ajouter cinq devoirs avec des échéances différentes
                await interaction.response.defer()
                await self.generate_debug_homeworks()
                await interaction.followup.send("Les devoirs de débogage ont été générés.", delete_after=5)

            @discord.ui.button(label="Supprimer des devoirs", style=discord.ButtonStyle.danger)
            async def delete_homeworks(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Demander le type de suppression
                delete_view = DeleteOptionsView(self.ctx)
                await interaction.response.send_message(
                    "Choisissez une option de suppression :",
                    view=delete_view,
                    delete_after=15  # Le message sera supprimé après 15 secondes
                )

            @discord.ui.button(label="Annuler", style=discord.ButtonStyle.grey)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("Opération annulée.", delete_after=5)
                self.stop()
                # Supprimer le menu des paramètres
                if self.message:
                    await self.message.delete()

            async def generate_debug_homeworks(self):
                guild_id = str(self.ctx.guild.id)
                guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})
                tz = pytz.timezone('Europe/Paris')
                now = datetime.now(tz)

                intervals = [1, 2, 3, 5, 7]  # Jours d'échéance pour les devoirs de débogage
                role_name = "debug"
                role = discord.utils.get(self.ctx.guild.roles, name=role_name)
                if not role:
                    # Créer le rôle de débogage s'il n'existe pas
                    role = await self.ctx.guild.create_role(name=role_name)

                for i, days in enumerate(intervals):
                    due_date = now + timedelta(days=days)
                    date_str = due_date.strftime('%d-%m-%Y')
                    time_str = due_date.strftime('%H:%M:%S')
                    titre = f"Devoir de débogage {i+1}"

                    devoir_data = {
                        'date': date_str,
                        'heure': time_str,
                        'titre': titre,
                        'guild_id': self.ctx.guild.id,
                        'role_to_ping': role.id,
                        'reminders_sent': [],
                        'debug': True  # Marqueur pour indiquer que c'est un devoir de débogage
                    }

                    # Créer un événement Discord
                    event_id = None
                    try:
                        event = await self.ctx.guild.create_scheduled_event(
                            name=titre,
                            start_time=due_date,
                            end_time=due_date + timedelta(hours=1),
                            entity_type=discord.EntityType.external,
                            privacy_level=discord.PrivacyLevel.guild_only,
                            location="Discord"
                        )
                        event_id = event.id
                    except Exception as e:
                        logging.error(f"Erreur lors de la création de l'événement Discord : {e}")

                    if event_id:
                        devoir_data['event_id'] = event_id

                    guild_data['devoirs'].append(devoir_data)

                save_data(data)

        # Classe pour la sélection des canaux
        class ChannelSelect(discord.ui.Select):
            def __init__(self, options, ctx):
                super().__init__(placeholder="Sélectionnez un canal...", options=options)
                self.ctx = ctx  # Stocker le contexte pour une utilisation ultérieure

            async def callback(self, interaction: discord.Interaction):
                channel_id = int(self.values[0])
                channel = self.ctx.guild.get_channel(channel_id)
                guild_id = str(self.ctx.guild.id)
                guild_data = data['guilds'].setdefault(guild_id, {'devoirs': [], 'settings': {}})
                guild_data['settings']['reminder_channel_id'] = channel_id
                save_data(data)
                await interaction.response.send_message(f"Le canal des rappels a été défini sur {channel.mention}.", delete_after=5)
                self.view.stop()

        # Classe pour la configuration des intervalles
        class IntervalsView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=10)  # Réduction du timeout à 10 secondes
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
                # Optionnellement, supprimer le message associé si vous le stockez

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
                await interaction.response.send_message("Les intervalles de rappels ont été mis à jour.", delete_after=5)
                self.parent_view.stop()

        # Classe pour la sélection des options de suppression
        class DeleteOptionsView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=10)  # Réduction du timeout à 10 secondes
                self.ctx = ctx

            async def on_timeout(self):
                # Désactiver les boutons lorsque le temps est écoulé
                for child in self.children:
                    child.disabled = True

        @discord.ui.button(label="Supprimer les devoirs de débogage", style=discord.ButtonStyle.danger)
        async def delete_debug(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            await self.delete_homeworks(debug_only=True)
            await interaction.followup.send("Les devoirs de débogage ont été supprimés.", delete_after=5)
            self.stop()

        @discord.ui.button(label="Supprimer tous les devoirs", style=discord.ButtonStyle.danger)
        async def delete_all(self, interaction: discord.Interaction, button: discord.ui.Button):
            confirm_view = ConfirmView(self.ctx)
            await interaction.response.send_message(
                "⚠️ **ATTENTION** ⚠️\n\nÊtes-vous sûr de vouloir supprimer **tous les devoirs** et les événements associés ? Cette action est irréversible.",
                view=confirm_view,
                delete_after=15  # Le message sera supprimé après 15 secondes
            )
            self.stop()

        @discord.ui.button(label="Annuler", style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Opération annulée.", delete_after=5)
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
                super().__init__(timeout=10)  # Réduction du timeout à 10 secondes
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
                for devoir in guild_data['devoirs']:
                    if 'event_id' in devoir:
                        try:
                            event = await guild.fetch_scheduled_event(devoir['event_id'])
                            await event.delete()
                        except Exception as e:
                            logging.error(f"Erreur lors de la suppression de l'événement Discord : {e}")

                # Vider la liste des devoirs
                guild_data['devoirs'].clear()
                save_data(data)

                await interaction.followup.send("Tous les devoirs et les événements associés ont été supprimés.", delete_after=5)
                self.stop()

            @discord.ui.button(label="Annuler", style=discord.ButtonStyle.grey)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("Suppression annulée.", delete_after=5)
                self.stop()

        # Envoyer le message du menu des paramètres
        view = SettingsView(ctx)
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # Enregistrer le message dans la vue pour pouvoir le gérer

    # Gestion des erreurs pour permissions manquantes
    @settings.error
    async def settings_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Vous devez être administrateur pour utiliser cette commande.", delete_after=5)
            # Supprimer le message de l'utilisateur après avoir informé de l'erreur
            try:
                await ctx.message.delete(delay=5)
            except Exception as e:
                logging.error(f"Impossible de supprimer le message de commande : {e}")
        else:
            raise error
