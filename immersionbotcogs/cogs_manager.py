import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import modals.help_text as help_text
import datetime, time
from modals.constants import tmw_id, _MULTIPLIERS, _JP_DB
from discord.app_commands import Choice
import json
from modals.sql import Set_jp
from modals.sql import Debug
from modals import helpers

start_time = time.time()

class BotManager(commands.Cog):
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)

    @app_commands.command(name="uptime", description="How long the bot is working.")
    async def uptime(self, interaction: discord.Interaction):

        channel = interaction.channel
        if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private:
            return await interaction.response.send_message(content='You can only log in #immersion-log or DMs.',ephemeral=True)

        current_time = time.time()
        difference = int(round(current_time - start_time))
        text = str(datetime.timedelta(seconds=difference))
        await interaction.response.send_message(content=f'Current uptime is {text}', ephemeral=True)

    @app_commands.command(name="reload_cog", description="Reloads cogs.")
    @app_commands.checks.has_role("Moderator")
    async def reload_cog(self, interaction: discord.Interaction):
        interaction.channel

        my_view = CogSelectView(timeout=1800)
        for cog_name in [extension for extension in self.bot.extensions]:
            cog_button = ReloadButtons(self.bot, label=cog_name)
            my_view.add_item(cog_button)
        await interaction.response.send_message(f"Please select the cog you would like to reload.",
                                                view=my_view,
                                                ephemeral=True)
    
    @app_commands.command(name="sync", description="Syncs slash commands to the guild.")
    @app_commands.checks.has_role("Moderator")
    async def sync(self, interaction: discord.Interaction):
        await self.bot.tree.sync()
        await interaction.response.send_message(f'Synced commands to guild with id {tmw_id}.')
        
    @app_commands.command(name="maintenance", description="Disables command usage for debugging.")
    @app_commands.checks.has_role("Moderator")
    async def maintenance(self, interaction: discord.Interaction, message: str):
        with Debug("dbs/debug.db") as debug:
            bool, msg = helpers.check_maintenance()
            if bool:
                debug.end_maintenance()
                return await interaction.response.send_message(content="Ended maintenance.", ephemeral=True)
            else:
                debug.start_maintenance(interaction.user.id, message)
                return await interaction.response.send_message(content=f"Started maintenance with the following info: {message}.", ephemeral=True)
        
    @app_commands.command(name='load', description='Loads cogs.')
    @app_commands.checks.has_any_role("Moderator")
    async def load(self, interaction: discord.Interaction,):
        my_view = CogSelectView(timeout=1800)
        for cog_name in [extension for extension in os.listdir('immersionbotcogs/') if extension.endswith('.py')]:
            cog_button = LoadButtons(self.bot, label=cog_name)
            my_view.add_item(cog_button)
        await interaction.response.send_message(f"Please select the cog you would like to reload.",
                                                view=my_view,
                                                ephemeral=True)
        
    @app_commands.command(name='clear_global_commands', description='Clears all global commands.')
    @app_commands.checks.has_any_role("Moderator")
    async def clear_global_commands(self, interaction: discord.Interaction):
        self.bot.tree.clear_commands(guild=interaction.guild)
        await interaction.response.send_message("Cleared global commands.")

    @app_commands.command(name='output_dist', description='Shows total output in channels.')
    @app_commands.checks.has_any_role("Moderator")
    async def output_dist(self, interaction: discord.Interaction):
        await interaction.response.defer()
        with Set_jp(_JP_DB) as store:
            outputs = store.all_output()
            dict = {}
            for output in outputs:
                channel_id, amount = output
                channel_name = interaction.guild.get_channel(channel_id).name
                dict[channel_name] = amount
    
        await interaction.followup.send(content=dict, ephemeral=True)
                

    @app_commands.command(name='multiplier', description=f'Adjust points multipliers.')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading"), Choice(name="Output", value="Output")])
    @app_commands.checks.has_any_role("Moderator")
    async def multiplier(self, interaction: discord.Interaction, media_type: str, amount: float):
        file_path = _MULTIPLIERS
        try:
            with open(file_path, "r") as file:
                MULTIPLIERS = json.load(file)
        except FileNotFoundError:
            MULTIPLIERS = {}

        # Adding a new entry to the dictionary
        old_amount = MULTIPLIERS[media_type.upper()]
        MULTIPLIERS[media_type.upper()] = amount

        # Save the updated dictionary back to the file
        with open(file_path, "w") as file:
            json.dump(MULTIPLIERS, file)

        await interaction.response.send_message(content=f'Changed multiplier for {media_type} from {old_amount} to {amount}.', ephemeral=True)

    @app_commands.command(name='help', description='Explains commands.')
    async def help(self, interaction: discord.Interaction):
        channel = interaction.channel
        if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private:
            return await interaction.response.send_message(content='You can only log in #immersion-log or DMs.',ephemeral=True)
            
        my_view = MyView(timeout=1800)
        for cog_name in [extension for extension in self.bot.extensions] + ["immersionbotcogs.BOT"]:
            if cog_name == "immersionbotcogs.cogs_manager":
                continue
            if cog_name == "immersionbotcogs.adjust":
                continue
            if cog_name == "immersionbotcogs.set_goal_media":
                continue
            if cog_name == "immersionbotcogs.set_goal_points":
                cog_name = "immersionbotcogs.set_goal"
            if cog_name == "immersionbotcogs.goals_manager":
                continue
            if cog_name == "immersionbotcogs.japanese_tracker":
                cog_name = "immersionbotcogs.output recognition"
            cog_button = ExplainButtons(self.bot, label=cog_name[17:])
            my_view.add_item(cog_button)

        await interaction.response.send_message(f"Please select the command you want to be explained.",
                                                view=my_view,
                                                ephemeral=True)

class MyView(discord.ui.View):
    def __init__(self, *, timeout: float = 1800):
        super().__init__(timeout=timeout)

class ExplainButtons(discord.ui.Button):

    def __init__(self, bot: commands.Bot, label):
        super().__init__(label=label)
        self.bot = bot

    async def callback(self, interaction):
        command = self.label
        await interaction.response.send_message(f'{help_text.HELP[command]}', ephemeral=True)
        await asyncio.sleep(25)
        await interaction.delete_original_response()

class CogSelectView(discord.ui.View):

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator

class ReloadButtons(discord.ui.Button):

    def __init__(self, bot: commands.Bot, label):
        super().__init__(label=label)
        self.bot = bot

    async def callback(self, interaction):
        cog_to_reload = self.label
        await self.bot.reload_extension(cog_to_reload)
        await interaction.response.send_message(f"Reloaded the following cog: {cog_to_reload}")
        print(f"Reloaded the following cog: {cog_to_reload}")
        await asyncio.sleep(10)
        await interaction.delete_original_response()

class ShowButton(discord.ui.Button):

    def __init__(self, bot: commands.Bot, label):
        super().__init__(label=label)
        self.bot = bot

    async def callback(self, interaction):
        return
        
class LoadButtons(discord.ui.Button):

    def __init__(self, bot: commands.Bot, label):
        super().__init__(label=label)
        self.bot = bot

    async def callback(self, interaction):
        cog_to_reload = self.label
        print(cog_to_reload, type(cog_to_reload))
        cog_to_reload = await self.bot.get_cog(cog_to_reload)
        await self.bot.load_extension(cog_to_reload)
        await interaction.response.send_message(f"Loaded the following cog: {cog_to_reload}")
        print(f"Loaded the following cog: {cog_to_reload}")
        await asyncio.sleep(10)
        await interaction.delete_original_response()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotManager(bot))
