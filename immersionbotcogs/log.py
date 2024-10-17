import discord
from discord.ext import commands
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice
from typing import List
from modals.sql import Store, Set_Goal
import modals.helpers as helpers
import logging
import aiohttp
import asyncio
from modals.constants import tmw_id, _DB_NAME, _GOAL_DB, _IMMERSION_CODES, _MULTIPLIERS
from modals.log_constructor import Log_constructor
import json

#############################################################

log = logging.getLogger(__name__)

#############################################################


class Log(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)

    @app_commands.command(name='log', description=f'Log your immersion')
    @app_commands.describe(amount='''Episodes watched, characters or pages read. Time read/listened in [hr:min:sec], [min:sec], [min] for example '1.30' or '25'.''')
    @app_commands.describe(comment='''Comment''')
    @app_commands.describe(name='''You can use vndb IDs and titles for VN and Anilist codes for Anime and Manga''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading")])
    async def log(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], comment: Optional[str]):
        #only allowed to log in #bot-debug, #immersion-logs, DMs
        #DMs not working
        channel = interaction.channel
        if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private and channel.id != 947813835715256393:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
        
        bool, msg = helpers.check_maintenance()
        if bool:
            return await interaction.response.send_message(content=f'In maintenance: {msg.maintenance_msg}', ephemeral=True)
        
        amount = helpers.amount_time_conversion(media_type, amount)
        if not amount.bool:
            return await interaction.response.send_message(ephemeral=True, content='Enter a valid number.')
        
        #introducing upperbound for amount to log for each media_type
        if not amount.value > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numbers allowed.')

        if media_type == "VN" and amount.value > 2000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 2 million allowed.')
        
        if media_type == "Manga" and amount.value > 3000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 1000 allowed.')
        
        if media_type == "Anime" and amount.value > 200:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 200 allowed.')
        
        if media_type == "Book" and amount.value > 500:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 500 allowed.')

        if media_type == "Readtime" and amount.value > 400:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 400 allowed.')

        if media_type == "Listening" and amount.value > 1000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 400 allowed.')

        if media_type == "Reading" and amount.value > 2000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 2 million allowed.')
        
        if amount.value in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')

        #max comment/name length
        if name != None:
            if len(name) > 150:
                return await interaction.response.send_message(ephemeral=True, content='Only name/comments under 150 characters allowed.')
        elif comment != None:
            if len(comment) > 150:
                return await interaction.response.send_message(ephemeral=True, content='Only name/comments under 150 characters allowed.')
        
        await interaction.response.defer()

        date = interaction.created_at
        with Set_Goal(_GOAL_DB) as store_goal:
            goals = store_goal.get_goals(interaction.user.id)
        
        first_date = date.replace(day=1, hour=0, minute=0, second=0)

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
        calc_amount, format, msg, immersion_title = helpers.point_message_converter(media_type.upper(), amount.value, name, MULTIPLIERS, codes, codes_path)
        print(first_date, date)
        with Store(_DB_NAME) as store_prod:
            old_points = store_prod.get_logs_by_user(interaction.user.id, None, (first_date, date), None)

            old_weighed_points_mediums = helpers.multiplied_points(old_points, MULTIPLIERS)

            old_rank_achievement, old_achievemnt_points, old_next_achievement, old_emoji, old_rank_name, old_next_rank_emoji, old_next_rank_name, id = helpers.check_achievements(interaction.user.id, media_type.upper(), store_prod, MULTIPLIERS)

            store_prod.new_log(tmw_id, interaction.user.id, media_type.upper(), amount.value, name, comment, date)
            
            current_rank_achievement, current_achievemnt_points, new_rank_achievement, new_emoji, new_rank_name, new_next_rank_emoji, new_next_rank_name, id = helpers.check_achievements(interaction.user.id, media_type.upper(), store_prod, MULTIPLIERS)


            current_points = store_prod.get_logs_by_user(interaction.user.id, None, (first_date, date), None)
        current_weighed_points_mediums = helpers.multiplied_points(current_points, MULTIPLIERS)

        if goals:
            log = Log_constructor(interaction.user.id, media_type, amount.value, name, comment, interaction.created_at)
            with Set_Goal(_GOAL_DB) as store_goal:
                goal_message = helpers.update_goals(interaction, goals, log, store_goal, media_type, MULTIPLIERS, codes, codes_path)
            with Set_Goal(_GOAL_DB) as store_goal:
                goals = store_goal.get_goals(interaction.user.id)
            store_goal.close()
    
            goals_description = helpers.get_goal_description(goals, codes_path, codes)
            
        else:
            goals_description = []
            goal_message = []
        
        def emoji():
            emoji = helpers.get_emoji(media_type.upper(), amount.value, immersion_title[0])
            if emoji == None:
                emoji = ""
            
            return emoji

        def add_suffix_to_date(date):
            day = date.day
            suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            return f"{date.strftime('%b')} {day}{suffix} {date.strftime('%Y')}"

        def created_embed():
            embed = discord.Embed(title=f'''Logged {round(amount.value,2)} {format} of {immersion_title[1]} {emoji()}''', description=f'{immersion_title[0]}\n\n{msg}\n{date.strftime("%B")}: ~~{helpers.millify(sum(i for i, j in list(old_weighed_points_mediums.values())))}~~ → {helpers.millify(sum(i for i, j in list(current_weighed_points_mediums.values())))}', color=discord.Colour.random())
            with Store(_DB_NAME) as store_prod:
                embed.add_field(name='Streak', value=f'current streak: **{store_prod.get_log_streak(interaction.user.id)[0].current_streak} days**')
            if new_next_rank_name != "Master" and old_next_achievement == new_rank_achievement:
                embed.add_field(name='Next Achievement', value=media_type.upper() + " " + new_next_rank_name + " " + new_next_rank_emoji + " in " + str(round(new_rank_achievement-current_achievemnt_points, 2)) + " " + helpers.media_type_format(media_type.upper()))
            elif old_next_achievement != new_rank_achievement:
                embed.add_field(name='Next Achievement', value=media_type.upper() + " " + new_next_rank_name + " " + new_next_rank_emoji + " " + str(int(new_rank_achievement)) + " " + helpers.media_type_format(media_type.upper()), inline=True)
            if goals_description:
                embed.add_field(name='Goals', value='\n'.join(goals_description), inline=False)
            #embed.add_field(name='Breakdown', value=f'{date.strftime("%B")}: ~~{helpers.millify(sum(i for i, j in list(old_weighed_points_mediums.values())))}~~ → {helpers.millify(sum(i for i, j in list(current_weighed_points_mediums.values())))}')
            embed.set_footer(text=f'From {interaction.user.display_name} on {add_suffix_to_date(interaction.created_at)}', icon_url=interaction.user.display_avatar.url)
            if immersion_title[3]:
                url = immersion_title[3]
                if url != None:
                    embed.set_thumbnail(url=url)
            return embed
        
        await interaction.edit_original_response(embed=created_embed())
        if comment:
            await interaction.channel.send(content=">>> " + comment)
        if old_next_achievement != new_rank_achievement:
            await interaction.channel.send(content=f'{interaction.user.mention} congrats on unlocking the achievement {media_type.upper()} {new_rank_name} {new_emoji} {str(int(current_rank_achievement))} {helpers.media_type_format(media_type.upper())}!!! {emoji()}')

        store_prod.close()
        if goal_message != [] and goals:
            await interaction.channel.send(content=f'{goal_message[0][0]} congrats on finishing your goal of {goal_message[0][1]} {goal_message[0][2]} {goal_message[0][3]} {goal_message[0][4]}, keep the spirit!!! {goal_message[0][5]} {emoji()}')

    @log.autocomplete('name')
    async def log_autocomplete(self, interaction: discord.Interaction, current: str,) -> List[app_commands.Choice[str]]:

        await interaction.response.defer()
        media_type = interaction.namespace['media_type']
        suggestions = []
        url = ''

        if media_type == 'VN' or media_type == "READTIME":
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

        elif media_type == 'Listening':
            IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
            API_KEY = "860e1049661dfa0c1e872b32dc331e2c"
            query = current
            url = f"https://api.themoviedb.org/3/search/multi?api_key={API_KEY}&query={query}"

            # Define the parameters for the request
            params = {
                "api_key": API_KEY,
                "query": query
            }

        if not url:
            return []

        async with aiohttp.ClientSession() as session:
            if media_type == 'Listening':
                async with session.get(url, params=params) as resp:
                    log.info(f"Status: {resp.status}")
                    json_data = await resp.json()

                    if 'results' in json_data:
                        suggestions = [
                            (result.get('name') or result.get('title'), result.get('original_title'), result.get('original_language'), result['id'], result['media_type'], result.get('poster_path'))
                            for result in json_data['results']
                        ]
                    
                    await asyncio.sleep(0)
                    
                    return [
                        app_commands.Choice(name=f'{org_lan}: {title} ({org_title}) ({media_type})', value=str([id, media_type, f'{poster}']))
                        for title, org_title, org_lan, id, media_type, poster in suggestions if query.lower() in title.lower()
                    ]
            else:
                async with session.post(url, json=data) as resp:
                    log.info(resp.status)
                    json_data = await resp.json()

                    if media_type == 'VN' or media_type == "READTIME":
                        suggestions = [(result['title'], result['id']) for result in json_data['results']]

                    elif media_type == 'Anime' or media_type == 'Manga':
                        suggestions = [(f"{result['title']['romaji']} ({result['title']['native']})", result['id']) for result in json_data['data']['Page']['media']]

                    await asyncio.sleep(0)

                    return [
                        app_commands.Choice(name=title, value=str(id))
                        for title, org_title, org_lan, id in suggestions if current.lower() in title.lower()
                    ]

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Log(bot))
