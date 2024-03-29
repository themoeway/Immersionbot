import discord
from discord.ext import commands
from typing import Optional
from discord import app_commands
from discord.app_commands import Choice
from typing import List
from sql import Store, Set_Goal
import helpers
import logging
import aiohttp
import asyncio
#############################################################

log = logging.getLogger(__name__)

#############################################################


class Log(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(617136488840429598)

    @app_commands.command(name='log', description=f'Log your immersion')
    @app_commands.describe(amount='''Episodes watched, characters or pages read. Time read/listened in [hr:min] or [min] for example '1.30' or '25'.''')
    @app_commands.describe(comment='''Comment''')
    @app_commands.describe(name='''You can use vndb IDs and titles for VN and Anilist codes for Anime and Manga''')
    @app_commands.choices(media_type = [Choice(name="Visual Novel", value="VN"), Choice(name="Manga", value="Manga"), Choice(name="Anime", value="Anime"), Choice(name="Book", value="Book"), Choice(name="Readtime", value="Readtime"), Choice(name="Listening", value="Listening"), Choice(name="Reading", value="Reading")])
    @app_commands.checks.has_role("QA Tester")
    async def log(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], comment: Optional[str]):
        #only allowed to log in #bot-debug, #immersion-logs, DMs
        #DMs not working
        channel = interaction.channel
        if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private:
            return await interaction.response.send_message(ephemeral=True, content='You can only log in #immersion-log or DMs.')
        
        amount = helpers.amount_time_conversion(media_type, amount)

        #introducing upperbound for amount to log for each media_type
        if not amount > 0:
            return await interaction.response.send_message(ephemeral=True, content='Only positive numbers allowed.')

        if media_type == "VN" and amount > 2000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 2 million allowed.')
        
        if media_type == "Manga" and amount > 1000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 1000 allowed.')
        
        if media_type == "Anime" and amount > 200:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 200 allowed.')
        
        if media_type == "Book" and amount > 500:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 500 allowed.')

        if media_type == "READTIME" and amount > 400:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 400 allowed.')

        if media_type == "LISTENING" and amount > 400:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 400 allowed.')

        if media_type == "READING" and amount > 2000000:
            return await interaction.response.send_message(ephemeral=True, content='Only numbers under 2 million allowed.')
        
        if amount in [float('inf'), float('-inf')]:
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

        store_goal = Set_Goal("goals.db")
        
        goals = store_goal.get_goals(interaction.user.id)
        
        store_prod = Store("prod.db")
        first_date = date.replace(day=1, hour=0, minute=0, second=0)
        calc_amount, format, msg, title = helpers.point_message_converter(media_type.upper(), amount, name)
        old_points = store_prod.get_logs_by_user(interaction.user.id, None, (first_date, date), None)
        
        old_weighed_points_mediums = helpers.multiplied_points(old_points)
        old_rank_achievement, old_achievemnt_points, old_next_achievement, old_emoji, old_rank_name, old_next_rank_emoji, old_next_rank_name, id = helpers.check_achievements(interaction.user.id, media_type.upper(), store_prod)

        store_prod.new_log(617136488840429598, interaction.user.id, media_type.upper(), amount, [title, comment], date)
        
        current_rank_achievement, current_achievemnt_points, new_rank_achievement, new_emoji, new_rank_name, new_next_rank_emoji, new_next_rank_name, id = helpers.check_achievements(interaction.user.id, media_type.upper(), store_prod)
    
        current_points = store_prod.get_logs_by_user(interaction.user.id, None, (first_date, date), None)
        current_weighed_points_mediums = helpers.multiplied_points(current_points)

        if goals:
            beginn = goals[0].created_at
            end = interaction.created_at
            relevant_logs = store_prod.get_logs_by_user(interaction.user.id, None, (beginn, end), None)
            if not relevant_logs:
                for goal_row in goals:
                    goals_description.append(f"""- 0/{goal_row.amount} {helpers.media_type_format(goal_row.media_type.value) if goal_row.goal_type != "POINTS" else "points"} {goal_row.text} ({goal_row.span}{"=" + str(goal_row.end) if goal_row.span == "DATE" else ""})""")
                goals_description = '\n'.join(goals_description)

            dicts = helpers.get_time_relevant_logs(goals, relevant_logs)
            goals_description, goal_message = helpers.get_goal_description(dicts=dicts, log_bool=True, store=store_goal, interaction=interaction, media_type=media_type)
        else:
            goals_description = []
        
        await interaction.edit_original_response(view=None,content=f'''{interaction.user.mention} logged {round(amount,2)} {format} {title} {helpers.random_emoji()}\n{msg}\ncurrent streak: **{store_prod.get_log_streak(interaction.user.id)[0].current_streak} days**\n\n{"""__Goal progression:__
""" + str(goals_description) + """
""" if goals_description else ""}{date.strftime("%B")}: ~~{helpers.millify(sum(i for i, j in list(old_weighed_points_mediums.values())))}~~ → {helpers.millify(sum(i for i, j in list(current_weighed_points_mediums.values())))}\n{("""
**Next Achievement: **""" + media_type.upper() + " " + new_next_rank_name + " " + new_next_rank_emoji + " in " + str(new_rank_achievement-current_achievemnt_points) + " " + helpers.media_type_format(media_type.upper())) if new_next_rank_name != "Master" else "" if old_next_achievement == new_rank_achievement else """
**New Achievemnt Unlocked: **""" + media_type.upper() + " " + new_rank_name + " " + new_emoji + " " + str(int(current_rank_achievement)) + " " + helpers.media_type_format(media_type.upper()) + """
**Next Achievement:** """ + media_type.upper() + " " + new_next_rank_name + " " + new_next_rank_emoji + " " + str(int(new_rank_achievement)) + " " + helpers.media_type_format(media_type.upper())}\n\n{">>> " + comment if comment else ""}''')
        if goal_message != []:
            await interaction.channel.send(content=f'{goal_message[0][0]} congrats on finishing your goal of {goal_message[0][1]} {goal_message[0][2]} {goal_message[0][3]} {goal_message[0][4]}, keep the spirit!!! {goal_message[0][5]}')
            
    @log.autocomplete('name')
    async def log_autocomplete(self, interaction: discord.Interaction, current: str,) -> List[app_commands.Choice[str]]:
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
                        id
                        title {{
                    media (search: $title, type: {media_type.upper()}) {{
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
    await bot.add_cog(Log(bot))