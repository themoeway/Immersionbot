import discord
from discord.ext import commands
from datetime import timedelta

from discord import app_commands


from pathlib import Path

import warnings

import pandas as pd


from enum import Enum
import sqlite3
from modals.sql import Store


import modals.helpers as helpers
from modals.constants import _DB_NAME,tmw_id, _MULTIPLIERS, _USER_NAMES_PATH

import json
import bar_chart_race as bcr
from pathlib import Path

class SqliteEnum(Enum):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return self.name

class MediaType(SqliteEnum):
    BOOK = 'BOOK'
    MANGA = 'MANGA'
    READTIME = 'READTIME'
    READING = 'READING'
    VN = 'VN'
    ANIME = 'ANIME'
    LISTENING = 'LISTENING'
    OUTPUT = 'OUTPUT'

class Announcement(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)
        
    async def generate_chart_race(logs, start_date, end_date, media_type=None, value_col=None, title=None, filename=None):
        if value_col is None:
            if media_type is None:
                value_col = 'cum_score'
            else:
                value_col = 'cum_amount'

        start_date = pd.to_datetime(start_date).tz_convert('UTC')
        end_date = pd.to_datetime(end_date).tz_convert('UTC')
        df = df[(df.created_at >= start_date) & (df.created_at < end_date)]
        if media_type is not None:
            df = df[df.media_type == media_type]
        df['cum_score'] = df.groupby('discord_user_id').score.cumsum()
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['cum_amount'] = df.groupby('discord_user_id')['amount'].cumsum()
        df = df.groupby(['user_name', 'date']).max().reset_index().pivot(index='date', columns='user_name', values=value_col)
        df = df.ffill().fillna(0)

        with warnings.catch_warnings():
            # suppress warnings cause of matplotlib spam
            warnings.simplefilter("ignore")

            bcr.bar_chart_race(
                df=df,
                n_bars=20,
                title=title,
                filter_column_colors=True,
                period_length=500,
                steps_per_period=20,
                shared_fontdict={
                    'family': 'Yu Mincho',
                    'weight': 'normal'
                },
                filename=filename,
            )
            
    async def get_user(id):
        user = self.bot.get_user(id)
        return user or await self.bot.fetch_user(id)
    
    async def get_user_names():
        with Store(_DB_NAME) as store:
            user_ids = store.get_users()
            
        user_names_path = _USER_NAMES_PATH
        try:
            with open(user_names_path, "r") as file:
                user_names = json.load(file)
        except FileNotFoundError:
            user_names = {}
            
        for user_id in user_ids:
            if user_id not in user_names.keys():
                try:
                    user = await self.get_user(user_id)
                    display_name = user.display_name if user else 'Unknown'
                except Exception:
                    display_name = 'Unknown'
                else:
                    user_names[user_id] = display_name
                    
        with open(user_names_path, "w") as file:
            json.dump(user_names, file)
        
        return user_names
            
    
    async def generate_all_chart_races(self, beginn, end, outdir):
        with Store(_DB_NAME) as store:
            logs = store.get_table('logs', beginn, end)
        user_names = await self.get_user_names()

        logs['created_at'] = pd.to_datetime(logs.created_at)
        logs['user_name'] = logs.discord_user_id.map(user_names)
        
        multipliers_path = _MULTIPLIERS
        try:
            with open(multipliers_path, "r") as file:
                MULTIPLIERS = json.load(file)
        except FileNotFoundError:
            MULTIPLIERS = {}

        logs['score'] = logs.media_type.map(MULTIPLIERS) * logs.amount
        logs = logs.sort_values('created_at')
        logs['score'] = pd.to_numeric(logs['score'], errors='coerce')
        logs['cum_score'] = logs.groupby('discord_user_id')['score'].cumsum()
        logs['date'] = logs.created_at.dt.date

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        month = beginn.strftime("%B")
        
        # ADD WINNER AND WINNER_POINTS
        # ADD announcement message with print(f'__**{media_type_str}**__\n' + ' '.join([f"{row['user_name']}" for _, row in top_users.iterrows()]))
        with Store(_DB_NAME) as store:
            f'''I want to congratulate {winner} for getting the first place in {month}'s immersion challenge with {winner_points} points! We had {store.count_unique_user((beginn, end))} participants in {month} logging {store.count_total_logs((beginn, end))} entries. {helpers.random_emoji()} {helpers.random_emoji()}'''
        
        #for media_type in ['OUTPUT']:
        for media_type in [None, 'ANIME', 'VN', 'MANGA', 'READING', 'LISTENING', 'READTIME', 'BOOK']:
            media_type_str = "overall" if media_type is None else media_type
            print(f'Processing {media_type_str}')
            filename = str(out_dir / f'chart_{media_type_str}.mp4')
            await self.generate_chart_race(logs, beginn, end, media_type, title=media_type, filename=filename)

            # Print top 20 users for each media type
            if media_type is None:
                top_users = logs.groupby('user_name').sum(numeric_only=True).nlargest(20, columns=['score']).reset_index()
            else:
                top_users = logs[logs.media_type == media_type].groupby('user_name').sum(numeric_only=True).nlargest(20, columns=['score']).reset_index()
            
            print(f'__**{media_type_str}**__\n' + ' '.join([f"{row['user_name']}" for _, row in top_users.iterrows()]))
    
    @app_commands.command(name='announcement', description=f'Releases the immersion challenge announcement.')
    @app_commands.describe(timeframe='''[year-month-day-year-month-day]''')
    async def announcement(self, interaction: discord.Interaction, timeframe: str):
        await interaction.response.defer()
        try:
            dates = timeframe.split('-')
            if len(timeframe.split('-')) == 6:
                beginn = interaction.created_at.replace(year=int(dates[0]), month=int(dates[1]), day=int(dates[2]))
                end = interaction.created_at.replace(year=int(dates[3]), month=int(dates[4]), day=int(dates[5]))
                f"""{beginn.strftime("{0} %b").format(helpers.ordinal(beginn.day))}-{end.strftime("{0} %b").format(helpers.ordinal(end.day))}"""
                if beginn > end:
                    return await interaction.response.send_message(content='You switched up the dates.', ephemeral=True)
            elif len(timeframe.split('-')) == 3:
                beginn = interaction.created_at.replace(year=int(dates[0]), month=int(dates[1]), day=int(dates[2]), hour=0, minute=0, second=0)
                end = beginn + timedelta(days=1)
                f"""{beginn.strftime("{0} %b").format(helpers.ordinal(beginn.day))}-{end.strftime("{0} %b").format(helpers.ordinal(end.day))}"""
                if beginn > interaction.created_at:
                    return await interaction.response.send_message(content='''You can't look into the future.''', ephemeral=True)
            else:
                return await interaction.response.send_message(content='Enter a valid date. [Year-Month-day] e.g 2023-12-24', ephemeral=True)
        except Exception:
            return await interaction.response.send_message(content='Enter a valid date. [Year-Month-day] e.g 2023-12-24', ephemeral=True)
        
        await self.generate_all_chart_races(beginn, end, out_dir=f'{beginn.strftime("%B").lower()}{beginn.year}')
        

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Announcement(bot))
