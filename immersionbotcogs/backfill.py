import discord
from discord.ext import commands
from datetime import timedelta
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice
from typing import List
from modals.sql import Store
import modals.helpers as helpers
import logging
import aiohttp
import asyncio
from modals.constants import tmw_id, _DB_NAME, _IMMERSION_CODES, _MULTIPLIERS
import json
#############################################################

log = logging.getLogger(__name__)

#############################################################

class Backfill(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)

    @app_commands.command(name='backfill', description=f'Backfill your immersion')
    @app_commands.describe(amount='''Episodes watched, characters or pages read. Time read/listened in [hr:min] or [min] for example '1.30' or '25'.''')
    @app_commands.describe(comment='''Comment''')
    @app_commands.describe(date='''[year-month-day] Example: '2023-12-24' ''')
    @app_commands.describe(name='''You can use vndb IDs and titles for VN and Anilist codes for Anime and Manga''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading")])
    async def backfill(self, interaction: discord.Interaction, date: str, media_type: str, amount: str, name: Optional[str], comment: Optional[str]):

        channel = interaction.channel
        if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private and channel.id != 947813835715256393:
            return await interaction.response.send_message(content='You can only backfill in #immersion-log or DMs.',ephemeral=True)
        
        bool, msg = helpers.check_maintenance()
        if bool:
            return await interaction.response.send_message(content=f'In maintenance: {msg.maintenance_msg}', ephemeral=True)
            
        amount = helpers.amount_time_conversion(media_type, amount)
        if not amount.bool:
            return await interaction.response.send_message(ephemeral=True, content='Enter a valid number.')
        
        #introducing upperbound for amount to log for each media_type
        if not amount.value > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numbers allowed.')

        if media_type == "VN" and amount.value > 4000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 4 million allowed.')
        
        if media_type == "Manga" and amount.value > 5000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 3000 allowed.')
        
        if media_type == "Anime" and amount.value > 200:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 200 allowed.')
        
        if media_type == "Book" and amount.value > 1000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 1000 allowed.')

        if media_type == "Readtime" and amount.value > 1000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 1000 allowed.')

        if media_type == "Listening" and amount.value > 1000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 1000 allowed.')

        if media_type == "Reading" and amount.value > 4000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 4 million allowed.')
        
        if amount.value in [float('inf'), float('-inf')]:
            return await interaction.response.send_message(ephemeral=True, content='No infinities allowed.')

        if name != None:
            if len(name) > 150:
                return await interaction.response.send_message(ephemeral=True, content='Only name/comments under 150 characters allowed.')
        elif comment != None:
            if len(comment) > 150:
                return await interaction.response.send_message(ephemeral=True, content='Only name/comments under 150 characters allowed.')

        try:
            date = interaction.created_at.replace(year=int(date.split('-')[0]), month=int(date.split('-')[1]), day=int(date.split('-')[2]))
            if date > interaction.created_at:
                return await interaction.response.send_message(content='''You can't backfill in the future.''', ephemeral=True)
            if date < interaction.created_at - timedelta(days=90):
                return await interaction.response.send_message(content='''You can't backfill more than 90 days in the past.''', ephemeral=True)
        except Exception:
            return await interaction.response.send_message(content='Enter a valid date. [Year-Month-day] e.g 2023-12-24', ephemeral=True)
        
        await interaction.response.defer()

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
            
        with Store(_DB_NAME) as store:
            first_date = date.replace(day=1, hour=0, minute=0, second=0)
            calc_amount, format, msg, immersion_title = helpers.point_message_converter(media_type.upper(), amount.value, name, MULTIPLIERS, codes, codes_path)
            old_points = store.get_logs_by_user(interaction.user.id, None, (first_date, date), None)
            old_weighed_points_mediums = helpers.multiplied_points(old_points, MULTIPLIERS)
            old_rank_achievement, old_achievemnt_points, old_next_achievement, old_emoji, old_rank_name, old_next_rank_emoji, old_next_rank_name, id = helpers.check_achievements(interaction.user.id, media_type.upper(), store, MULTIPLIERS)
            
            store.new_log(tmw_id, interaction.user.id, media_type.upper(), amount.value, name, comment, date)
            
            current_rank_achievement, current_achievemnt_points, new_rank_achievement, new_emoji, new_rank_name, new_next_rank_emoji, new_next_rank_name, id = helpers.check_achievements(interaction.user.id, media_type.upper(), store, MULTIPLIERS)
        
            current_points = store.get_logs_by_user(interaction.user.id, None, (first_date, date), None)
            current_weighed_points_mediums = helpers.multiplied_points(current_points, MULTIPLIERS)

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
            embed = discord.Embed(title=f'''Backfilled {round(amount.value,2)} {format} of {immersion_title[1]} {emoji()}''', description=f'{immersion_title[0]}\n\n{msg}\n{date.strftime("%B")}: ~~{helpers.millify(sum(i for i, j in list(old_weighed_points_mediums.values())))}~~ → {helpers.millify(sum(i for i, j in list(current_weighed_points_mediums.values())))}', color=discord.Colour.random())
            with Store(_DB_NAME) as store:
                embed.add_field(name='Streak', value=f'current streak: **{store.get_log_streak(interaction.user.id)[0].current_streak} days**')
            if new_next_rank_name != "Master" and old_next_achievement == new_rank_achievement:
                embed.add_field(name='Next Achievement', value=media_type.upper() + " " + new_next_rank_name + " " + new_next_rank_emoji + " in " + str(new_rank_achievement-current_achievemnt_points) + " " + helpers.media_type_format(media_type.upper()))
            elif old_next_achievement != new_rank_achievement:
                embed.add_field(name='Next Achievement', value=media_type.upper() + " " + new_next_rank_name + " " + new_next_rank_emoji + " " + str(int(new_rank_achievement)) + " " + helpers.media_type_format(media_type.upper()), inline=True)
            #embed.add_field(name='Breakdown', value=f'{date.strftime("%B")}: ~~{helpers.millify(sum(i for i, j in list(old_weighed_points_mediums.values())))}~~ → {helpers.millify(sum(i for i, j in list(current_weighed_points_mediums.values())))}')
            embed.set_footer(text=f'From {interaction.user.display_name} on {add_suffix_to_date(interaction.created_at)}', icon_url=interaction.user.display_avatar.url)
            if immersion_title[3]:
                url = immersion_title[3]
                if url != None:
                    embed.set_thumbnail(url=url)
            return embed
        
        store.close()
        await interaction.edit_original_response(embed=created_embed())
        
    @backfill.autocomplete('name')
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
    await bot.add_cog(Backfill(bot))
