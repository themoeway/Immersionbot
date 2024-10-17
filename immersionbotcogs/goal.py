import discord
from discord.ext import commands
from discord import app_commands
from modals.sql import Set_Goal
import time
import modals.helpers as helpers
from modals.constants import tmw_id, _GOAL_DB, _IMMERSION_CODES
import json

class Goal(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)

    @app_commands.command(name='goals', description=f'See your immersion log goal overview.')
    async def goals(self, interaction: discord.Interaction):
        
        bool, msg = helpers.check_maintenance()
        if bool:
            return await interaction.response.send_message(content=f'In maintenance: {msg.maintenance_msg}', ephemeral=True)
        
        with Set_Goal(_GOAL_DB) as store_goal:
            goals = store_goal.get_goals(interaction.user.id)
                
        if not goals:
            return await interaction.response.send_message(ephemeral=True, content='No goals found. Set goals with ``/set_goal``.')
        
        codes_path = _IMMERSION_CODES
        try:
            with open(codes_path, "r") as file:
                codes = json.load(file)
        except FileNotFoundError:
            codes = {}
        goals_description = helpers.get_goal_description(goals, codes_path, codes)
        goals_description = '\n'.join(goals_description)
        
        return await interaction.response.send_message(ephemeral=True, content=f'''## {interaction.user.display_name}'s Goal Overview\n{goals_description if goals_description else "No goals found."}\n\nUse ``/set_goal`` to set your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D> and more!''', suppress_embeds=True)

        
        # # dicts = helpers.get_time_relevant_logs(goals, relevant_logs)
        # goals_description, goal_message = helpers.get_goal_description(logs=relevant_logs, goals=goals, log_bool=False, store=store_goal, interaction=interaction, media_type=None)

        # await interaction.response.send_message(ephemeral=True, content=f'''## {interaction.user.display_name}'s Goal Overview\n{goals_description if goals_description else "No goals found."}\n\nUse ``/set_goal`` to set your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D> and more!''')
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Goal(bot))
