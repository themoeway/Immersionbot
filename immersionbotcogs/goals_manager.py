import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from typing import Optional
from datetime import timedelta
import pytz
from discord.ui import Select
from discord import app_commands
from modals.sql import Set_Goal
import modals.helpers as helpers
import json
from modals.constants import _GOAL_DB, _IMMERSION_CODES
from modals.goal import Goal

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

class Goals_manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.batch_update.start()
        
    def cog_unload(self):
        self.batch_update.cancel()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.batch_update.start()
        
    @app_commands.command(name='delete_goal', description=f'Delete an immersion goal.')
    async def delete_goal(self, interaction: discord.Interaction):
        
        bool, msg = helpers.check_maintenance()
        if bool:
            return await interaction.response.send_message(content=f'In maintenance: {msg.maintenance_msg}', ephemeral=True)
        
        with Set_Goal(_GOAL_DB) as store_goal:
            goals = store_goal.get_goals(interaction.user.id)
        if not goals:
            return await interaction.response.send_message(ephemeral=True, content='No goals found. Set goals with ``/set_goal``.')

        goals_description = []
        codes_path = _IMMERSION_CODES
        try:
            with open(codes_path, "r") as file:
                codes = json.load(file)
        except FileNotFoundError:
            codes = {}
        for goal_row in goals:
            try:
                updated_date = f'<t:{int(datetime.strptime(goal_row.end, "%Y-%m-%d %H:%M:%S.%f%z").timestamp())}:R>'
            except Exception:
                updated_date = goal_row.end
            goal_title = helpers.get_name_of_immersion(goal_row.media_type.value, goal_row.text, codes, codes_path)
            if goal_row.current_amount < goal_row.amount:
                    goals_description.append(f"""- {goal_row.current_amount}/{goal_row.amount} {helpers.media_type_format(goal_row.media_type.value) if goal_row.goal_type != "POINTS" else "points"} of [{goal_title[1]}]({goal_title[2]}) ({updated_date})""")
            else:
                goals_description.append(f"""~~- {goal_row.current_amount}/{goal_row.amount} {helpers.media_type_format(goal_row.media_type.value) if goal_row.goal_type != "POINTS" else "points"} of [{goal_title[1]}]({goal_title[2]}) ({updated_date})~~""")

        results = []
        for i, goal in enumerate(zip(goals_description, goals)):
            results.append((i + 1, goal, goal[1]))

        myembed = discord.Embed(title=f'Select a goal to delete:')
        for result in results[0:5]:
            myembed.add_field(name=f'{result[0]}. goal',value=f'{result[1][0]}', inline=False)
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
            with Set_Goal(_GOAL_DB) as store_goal:
                store_goal.delete_goal(interaction.user.id, relevant_result[2].media_type.value, relevant_result[2].amount, relevant_result[2].span)        
            await interaction.response.edit_message(content='## **Deleted goal.**')

        select.callback = my_callback
        view = MyView(data=results, beginning_index=beginning_index, end_index=end_index)
        
        view.add_item(select)
        store_goal.close()
        await interaction.response.send_message(embed=myembed, view=view, ephemeral=True)

    @tasks.loop(hours=24)
    async def batch_update(self):
        with Set_Goal(_GOAL_DB) as store:
            goals = store.get_all_goals()
            for goal in goals:
                if goal.span == "DAY" or goal.span == "DATE":
                    if pytz.utc.localize(datetime.now()) > datetime.strptime(goal.end, "%Y-%m-%d %H:%M:%S.%f%z").replace(tzinfo=pytz.UTC):
                        store.delete_goal(goal.discord_user_id, goal.media_type.value, goal.amount, goal.span)
                        store.delete_completed(goal.discord_user_id, goal.span, goal.amount, goal.media_type.value, goal.text)
                        continue
                    else:
                        continue
                elif goal.span == "WEEKLY" or goal.span == "DAILY":
                    if pytz.utc.localize(datetime.now()) > datetime.strptime(goal.end, "%Y-%m-%d %H:%M:%S.%f%z").replace(tzinfo=pytz.UTC):
                        if goal.span == "DAILY":
                            end = pytz.utc.localize(datetime.now()) + timedelta(days=1)
                            end.replace(hour=0, minute=0, second=0, microsecond=0)
                        else:
                            now = pytz.utc.localize(datetime.now())
                            created_at = now - timedelta(days=now.weekday())
                            end = created_at + timedelta(days=6)
                        print(end)
                        store.update_end(Goal(goal.discord_user_id, goal.goal_type, goal.media_type, goal.current_amount, goal.amount, goal.text, goal.span, goal.created_at, goal.end), end)
                        store.update_amount(Goal(goal.discord_user_id, goal.goal_type, goal.media_type, goal.current_amount, goal.amount, goal.text, goal.span, goal.created_at, goal.end), 0)
                    else:
                        continue
        store.close()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Goals_manager(bot))
