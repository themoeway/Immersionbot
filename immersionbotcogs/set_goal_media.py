import discord
from discord.ext import commands
from datetime import timedelta
from datetime import timedelta
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice
from modals.sql import Set_Goal, Store
import time
import modals.helpers as helpers
import aiohttp
from typing import List
import asyncio
import logging
from modals.goal import Goal
from modals.log_constructor import Log_constructor
from modals.sql import MediaType
from modals.constants import tmw_id, _GOAL_DB, _IMMERSION_CODES, _MULTIPLIERS, _DB_NAME
import json
#############################################################

log = logging.getLogger(__name__)

#############################################################

class Set_Goal_Media(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)
    
    @app_commands.command(name='set_goal_media', description=f'Set daily immersion log goals')
    @app_commands.describe(amount='''Episode to watch, characters or pages to read. Time to read/listen in [hr:min] or [min] for example '1.30' or '25'.''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading")])
    @app_commands.describe(name='''You can use vndb IDs for VN and Anilist codes for Anime, Manga and Light Novels''')
    @app_commands.describe(span='''[Day = Till the end of today], [Daily = Everyday], [Date = Till a certain date ([year-month-day] Example: '2022-12-29')]''')
    async def set_goal_media(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], span: str):
        
        bool, msg = helpers.check_maintenance()
        if bool:
            return await interaction.response.send_message(content=f'In maintenance: {msg}', ephemeral=True)
        
        amount = helpers.amount_time_conversion(media_type, amount)
        if not amount.bool:
            return await interaction.response.send_message(ephemeral=True, content='Enter a valid number.')
        
        #introducing upperbound for amount to log for each media_type
        if not amount.value > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numbers allowed.')

        if media_type == "VN" and amount.value > 4000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 4 million allowed.')
        
        if media_type == "Manga" and amount.value > 10000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 10000 allowed.')
        
        if media_type == "Anime" and amount.value > 20000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 20000 allowed.')
        
        if media_type == "Book" and amount.value > 10000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 10000 allowed.')

        if media_type == "Readtime" and amount.value > 40000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 40000 allowed.')

        if media_type == "Listening" and amount.value > 40000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 40000 allowed.')

        if media_type == "Reading" and amount.value > 4000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 4 million allowed.')
        
        if amount.value in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')
        
        if span.upper() == "DAY":
            span = "DAY"
            created_at = interaction.created_at.replace(hour=0, minute=0, second=0)
            end = interaction.created_at.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        elif span.upper() == "DAILY":
            span = "DAILY"
            created_at = interaction.created_at.replace(hour=0, minute=0, second=0)
            end = interaction.created_at + timedelta(days=1)
        elif span.upper() == "WEEKLY":
            span = "WEEKLY"
            created_at = interaction.created_at - timedelta(days=interaction.created_at.weekday())
            end = created_at + timedelta(days=6)
        elif span.upper() == "MONTHLY":
            span = "MONTHLY"
            created_at = interaction.created_at.replace(day=1)
            next_month = interaction.created_at.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
        else:
            created_at = interaction.created_at
            try:
                end = interaction.created_at.replace(year=int((span.split("-"))[0]), month=int((span.split("-"))[1]), day=int((span.split("-"))[2]), hour=0, minute=0, second=0)
                if end > interaction.created_at + timedelta(days=366):
                    return await interaction.response.send_message(content='''A goal span can't be longer than a year.''', ephemeral=True)
                if end < interaction.created_at:
                    return await interaction.response.send_message(content='''You can't set a goal in the past.''', ephemeral=True)
            except Exception:
                return await interaction.response.send_message(ephemeral=True, content='Please enter the date in the correct format.')
            else:
                span = "DATE"
                if end < created_at:
                    return await interaction.response.send_message(ephemeral=True, content='''You can't set goals for the past.''')

        goal_type = "MEDIA" if not name else "SPECIFIC"
        with Set_Goal(_GOAL_DB) as store:
            bool = store.check_goal_exists(interaction.user.id, goal_type, span, media_type.upper(), name)
            if bool:
                return await interaction.response.send_message(ephemeral=True, content='You already set this goal.')

            if len(store.get_goals(interaction.user.id)) > 10:
                return await interaction.response.send_message(ephemeral=True, content='''You can't set more than 10 goals. To delete a goal do ```/delete_goal``''')
            if not name:
                name = ""
                
            if goal_type == "SPECIFIC" and media_type == "LISTENING":
                store.new_goal(interaction.user.id, goal_type, media_type.upper(), 0, amount.value, str(eval(name)).replace("'", "''"), span, created_at, end)
            else:
                store.new_goal(interaction.user.id, goal_type, media_type.upper(), 0, amount.value, name, span, created_at, end)
        
        multipliers_path = _MULTIPLIERS
        try:
            with open(multipliers_path, "r") as file:
                MULTIPLIERS = json.load(file)
        except FileNotFoundError:
            MULTIPLIERS = {}
            
        codes_path = _IMMERSION_CODES
        try:
            with open(codes_path, "r") as file:
                codes = json.load(file)
        except FileNotFoundError:
            codes = {}
        with Store(_DB_NAME) as store_log:
            logs = store_log.get_logs_by_user(interaction.user.id, media_type, (created_at, end), None)
        store.close()
        goal_msgs = []
        for log in logs:
            with Set_Goal(_GOAL_DB) as store:
                goal_msg = helpers.update_goals(interaction.user.id, [Goal(interaction.user.id, goal_type, MediaType[media_type.upper()], 0, amount.value, name, span, created_at, end)], Log_constructor(interaction.user.id, log.media_type.value, log.amount, log.title, log.note, log.created_at), store, media_type, MULTIPLIERS, codes, codes_path)
                goal_msgs.append(goal_msg)
            
        codes_path = _IMMERSION_CODES
        try:
            with open(codes_path, "r") as file:
                codes = json.load(file)
        except FileNotFoundError:
            codes = {}
        name = helpers.get_name_of_immersion(media_type, name, codes, _IMMERSION_CODES)
        try:
            updated_date = f'<t:{int(end.timestamp())}:R>'
        except Exception:
            updated_date = end
        await interaction.response.send_message(ephemeral=True, content=f'''## Set {goal_type} goal as {span} goal\n- {amount.value} {helpers.media_type_format(media_type.upper())} of [{name[1]}]({name[2]}) ({updated_date})\n\nUse ``/goals`` to view your goals for <t:{int(time.mktime((interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0)).timetuple()))}:D>''', suppress_embeds=True)
        if goal_msgs:
            for goal_message in goal_msgs:
                await interaction.channel.send(content=f'{goal_message[0][0]} congrats on finishing your goal of {goal_message[0][1]} {goal_message[0][2]} {goal_message[0][3]} {goal_message[0][4]}, keep the spirit!!! {goal_message[0][5]} {helpers.random_emoji()}')

    @set_goal_media.autocomplete('name')
    async def log_autocomplete(self, interaction: discord.Interaction, current: str,) -> List[app_commands.Choice[str]]:

        await interaction.response.defer()
        media_type = interaction.namespace['media_type']
        suggestions = []
        url = ''

        if media_type == 'VN':
            url = 'https://api.vndb.org/kana/vn'
            data = {'filters': ['search', '=', f'{current}'], 'fields': 'title, alttitle'} # default no. of results is 10
        
        elif media_type == 'Anime' or media_type == 'Manga':
            url = 'https://graphql.anilist.co'
            query = f'''
            query ($page: Int, $perPage: Int, $title: String) {{
                Page(page: $page, perPage: $perPage) {{
                    pageInfo {{
                        total
                        perPage
                    }}
                    media (search: $title, type: {media_type.upper()}) {{
                        id
                        title {{
                            romaji
                            native
                        }}
                    }}
                }}
            }}
            '''

            variables = {
                'title': current,
                'page': 1,
                'perPage': 10
            }

            data = {'query': query, 'variables': variables}

        if not url:
            return []

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as resp:
                log.info(resp.status)
                json_data = await resp.json()

                if media_type == 'VN':
                    suggestions = [(result['title'], result['id']) for result in json_data['results']]

                elif media_type == 'Anime' or media_type == 'Manga':
                    suggestions = [(f"{result['title']['romaji']} ({result['title']['native']})", result['id']) for result in json_data['data']['Page']['media']]

                await asyncio.sleep(0)

                return [
                    app_commands.Choice(name=title, value=str(id))
                    for title, id in suggestions if current.lower() in title.lower()
                ]
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Set_Goal_Media(bot))
