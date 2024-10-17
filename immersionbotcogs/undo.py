import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from modals.sql import Store, Set_Goal
from typing import Optional
import json
from modals.constants import _DB_NAME, TIMEFRAMES, tmw_id, _GOAL_DB, _MULTIPLIERS, _IMMERSION_CODES
from modals.constants import tmw_id, _DB_NAME
from modals.log import Log
from modals import helpers
from discord.ui import Select

class MyView(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 900, data, beginning_index: int, end_index: int):
        super().__init__(timeout=timeout)
        self.data: list = data
        self.beginning_index: int = beginning_index
        self.ending_index: int = end_index
    
    
    async def edit_embed(self, data, beginning_index, ending_index):
        myembed = discord.Embed(title=f'Select a goal to delete:')
        for result in data[beginning_index:ending_index]:
            myembed.add_field(name=f'{result[0]}. goal',value=f'{result[1]}', inline=False)
        if len(data) >= 5:
            myembed.set_footer(text="... not all results displayed but you can pick any index.\n" 
                                    "Pick an index to retrieve a scene next.")
        else:
            myembed.set_footer(text="Pick an index to retrieve a scene next.")
        return myembed
        
        
    @discord.ui.button(label='≪', style=discord.ButtonStyle.grey, row=1)
    async def go_to_first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.beginning_index -=5
        self.ending_index -=5
        if self.beginning_index >= len(self.data):
            self.beginning_index = 0
            self.ending_index =5
        myembed = await self.edit_embed(self.data, self.beginning_index, self.ending_index)
        await interaction.response.edit_message(embed=myembed)
        
        
    @discord.ui.button(label='Back', style=discord.ButtonStyle.blurple, row=1)
    async def go_to_previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.beginning_index -= 5
        self.ending_index -= 5
        myembed = await self.edit_embed(self.data, self.beginning_index, self.ending_index)
        await interaction.response.edit_message(embed=myembed)
    
    
    @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple, row=1)
    async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.beginning_index += 5
        self.ending_index += 5
        myembed = await self.edit_embed(self.data, self.beginning_index, self.ending_index)
        await interaction.response.edit_message(embed=myembed)
        
        
    @discord.ui.button(label='≫', style=discord.ButtonStyle.grey, row=1)
    async def go_to_last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.beginning_index +=5
        self.ending_index +=5
        if self.beginning_index >= len(self.data):
            self.beginning_index -=5
            self.ending_index -=5
        myembed = await self.edit_embed(self.data, self.beginning_index, self.ending_index)
        await interaction.response.edit_message(embed=myembed)

class Undo(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)
                
    @app_commands.command(name='undo_log', description=f'Undo your latest immersion log.')
    @app_commands.describe(timeframe='''DEFAULT=MONTH; Week, Month, Year, All, [year-month-day] or [year-month-day-year-month-day]''')
    async def undo_log(self, interaction: discord.Interaction, timeframe: Optional[str]):
        
        interaction.channel
        # if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private:
        #     return await interaction.response.send_message(content='You can only log in #immersion-log or DMs.', ephemeral=True)
        
        bool, msg = helpers.check_maintenance()
        if bool:
            return await interaction.response.send_message(content=f'In maintenance: {msg}', ephemeral=True)
        
        if not timeframe or timeframe.upper() == "MONTH":
            #Month
            beginn = interaction.created_at.replace(day=1, hour=0, minute=0)
            end = (beginn.replace(day=28) + timedelta(days=4)) - timedelta(days=(beginn.replace(day=28) + timedelta(days=4)).day)

        elif timeframe.upper() == "WEEK":
            beginn = (interaction.created_at - timedelta(days=interaction.created_at.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (beginn + timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            
        elif timeframe.upper() == "YEAR":
            beginn = interaction.created_at.date().replace(month=1, day=1)
            end = interaction.created_at.date().replace(month=12, day=31)
            
        elif timeframe.upper() == "ALL":
            beginn = interaction.created_at.replace(year=2020)
            end = interaction.created_at
            
        elif timeframe.upper() not in TIMEFRAMES:
            try:
                dates = timeframe.split('-')
                if len(timeframe.split('-')) == 6:
                    beginn = interaction.created_at.replace(year=int(dates[0]), month=int(dates[1]), day=int(dates[2]))
                    end = interaction.created_at.replace(year=int(dates[3]), month=int(dates[4]), day=int(dates[5]))
                    if beginn > end:
                        return await interaction.response.send_message(content='You switched up the dates.', ephemeral=True)
                elif len(timeframe.split('-')) == 3:
                    beginn = interaction.created_at.replace(year=int(dates[0]), month=int(dates[1]), day=int(dates[2]), hour=0, minute=0, second=0)
                    end = beginn + timedelta(days=1)
                    if beginn > interaction.created_at:
                        return await interaction.response.send_message(content='''You can't look into the future.''', ephemeral=True)
                else:
                    return await interaction.response.send_message(content='Enter a valid date. [Year-Month-day] e.g 2023-12-24', ephemeral=True)
            except Exception:
                return await interaction.response.send_message(content='Enter a valid date. [Year-Month-day] e.g 2023-12-24', ephemeral=True)
            
        with Store(_DB_NAME) as store:
            logs = store.get_logs_by_user_with_row_id(interaction.user.id, None, (beginn, end), None)
        if logs == []:
            return await interaction.response.send_message(content='No logs were found. Try searching with a bigger timeframe.',ephemeral=True)
        
        # await interaction.response.defer()
        
        results = []
        for i, log in enumerate(logs):
            results.append((i + 1, log))

        myembed = discord.Embed(title=f'Select a log to delete:')
        for result in results[0:5]:
            myembed.add_field(name=f'{result[0]}. log',value=f'{result[1].created_at}: {result[1].media_type.value} {result[1].amount} {helpers.media_type_format(result[1].media_type.value)} {result[1].title if not None else ""} {result[1].note if not None else ""}', inline=False)
        if len(results) >= 5:
            myembed.set_footer(text="... not all results displayed but you can pick any index.\n"
                                "Pick an index to retrieve a scene next.")
        else:
            myembed.set_footer(text="Pick an index to retrieve a scene next.")
        beginning_index = 0
        end_index = 5
        
        options = []
        for result in results[0:5]:
            item = discord.SelectOption(label=f'{result[0]}')
            options.append(item)
            
        select = Select(min_values = 1, max_values = 1, options=options)
        async def my_callback(interaction):
            relevant_result = select.view.data[(int(select.values[0])-1) + int(select.view.beginning_index)]
            with Store(_DB_NAME) as store:
                store.delete_log(relevant_result[1].rowid)
            with Set_Goal(_GOAL_DB) as store_goal:
                goals = store_goal.get_goals(interaction.user.id)
            multipliers_path = _MULTIPLIERS
            try:
                with open(multipliers_path, "r") as file:
                    MULTIPLIERS = json.load(file)
            except FileNotFoundError:
                MULTIPLIERS = {}
            codes_path = _IMMERSION_CODES
            try:
                with open(codes_path, "r") as file:
                    json.load(file)
            except FileNotFoundError:
                pass
            log = Log(interaction.user.id, relevant_result[1].media_type.value, relevant_result[1].amount, relevant_result[1].title, relevant_result[1].note, relevant_result[1].created_at)
            with Set_Goal(_GOAL_DB) as store_goal:
                helpers.undo_goal(goals, log, store_goal, MULTIPLIERS)
            store_goal.close()
            await interaction.response.edit_message(content='## **Deleted log.**')

        select.callback = my_callback
        view = MyView(data=results, beginning_index=beginning_index, end_index=end_index)
        
        view.add_item(select)
        store.close()
        await interaction.response.send_message(embed=myembed, view=view, ephemeral=True)

        # store = Store(_DB_NAME)
        # log = store.get_that_log(interaction.user.id)
        # store.delete_log(interaction.user.id, log.media_type.value, log.amount, log.note)
        # return await interaction.followup.send(content='Deleted log.', ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Undo(bot))
