from collections import defaultdict
import math
import itertools
from enum import Enum
import sqlite3
from vndb_thigh_highs import VNDB
from vndb_thigh_highs.models import VN
from datetime import datetime, timedelta
from AnilistPython import Anilist
import random
from modals.constants import ACHIEVEMENTS, PT_ACHIEVEMENTS, ACHIEVEMENT_RANKS, ACHIEVEMENT_EMOJIS, ACHIEVEMENT_IDS, EMOJI_TABLE, JACK_FILTER

from modals.sql import Debug

def check_maintenance():
    with Debug("dbs/debug.db") as debug:
        m = debug.check_maintenance()
        msg = m.maintenance_msg
        return m.bool, msg

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
    ANYTHING = 'ANYTHING'

class Span(Enum):
    DAILY = "DAILY"
    DAY = "DAY"
    DATE = "DATE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

def get_title(title, media_type):
    if media_type:
        return f'''{title} {media_type} Leaderboard ({media_type_format(media_type)})'''
    else:
        return f'''{title} Leaderboard (pts)'''

import asyncio

async def get_leaderboard(bot, leaderboard, command_user, media_type, title, MULTIPLIERS):
    user_rank = [rank for uid, total, rank in leaderboard if uid == command_user.id]
    user_rank = user_rank and user_rank[0]

    async def get_user(id):
        user = bot.get_user(id)
        return user or await bot.fetch_user(id)

    async def leaderboard_row(user_id, points, rank):
        ellipsis = '...\n' if user_rank and rank == (user_rank-1) and rank > 21 else ''
        try:
            user = await get_user(user_id)
            display_name = user.display_name if user else 'Unknown'
        except Exception:
            display_name = 'Unknown'
        if media_type == "OUTPUT":
            amount = points
        elif media_type and media_type != "OUTPUT":
            amount = points / MULTIPLIERS[media_type]
        else:
            amount = _to_amount(media_type, points) if media_type else points
        return f'{ellipsis}**{make_ordinal(rank)} {display_name}**: {millify(amount)}'

    leaderboard_desc = '\n'.join(await asyncio.gather(*[leaderboard_row(*row) for row in leaderboard]))
    title = get_title(title, media_type)

    return title, leaderboard_desc

import re
def regex_jp_contents(content, regex):
    content = re.sub(r'「.*」|『.*』', '', content)
    characters = re.findall(regex, content)

    if not characters:
        return 0
    
    duplicate_char = ""
    indicies = []
    count = 0
    #そおおおおおおおおおうですううううううううううううううううううううううううね → そおうですうね

    for i, char in enumerate(characters):
        if char == duplicate_char:
            indicies.append(i)
            count = 0
        else:
            duplicate_char = char
            count = count + 1

    new_characters = ""
    for i, char in enumerate(characters):
        if i not in indicies:
            new_characters = new_characters + char

    return len(''.join(new_characters))

def regex_latin_contents(content, regex):
    characters = re.findall(regex, content)

    return len(''.join(characters))

import pytz

def Span_to_datetime(Span, list):

    def no_goal_case():
        return (now.replace(tzinfo=pytz.UTC) + timedelta(days=9), now.replace(tzinfo=pytz.UTC) + timedelta(days=10))

    now = datetime.now()
    if Span.value == "DAILY":
        # start of today, end of today
        return (now.replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC), now.replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC) + timedelta(days=1))
    elif Span.value == "DAY":
        # start of today, end of today
        return (now.replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC), now.replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC) + timedelta(days=1))
    elif Span.value == "DATE":
        # oldest date goal creation, latest date goal creation end date
        if list:
            return (datetime.strptime(list[0].created_at, "%Y-%m-%d %H:%M:%S.%f%z"), datetime.strptime(list[-1].end, "%Y-%m-%d %H:%M:%S.%f%z"))
    #weekly, monthly will take the beginning day of each timeframe instead of the date when the command was used to set them
    elif Span.value == "WEEKLY":
        if list:
            start_of_week = now.replace(tzinfo=pytz.UTC) - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return (start_of_week, end_of_week)
    elif Span.value == "MONTHLY":
        if list:
            start_of_month = now.replace(day=1, tzinfo=pytz.UTC)
            next_month = now.replace(day=28, tzinfo=pytz.UTC) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
            return (start_of_month, end)
        
    return no_goal_case()

def get_time_relevant_logs(goals, relevant_logs):
    #refractor later, there gotta be a better way to do this
    dicts = defaultdict(lambda: defaultdict(lambda: 0))
    for span in Span:
        dicts[span]['goals'] = [goal for goal in goals if goal.span == span.value]
        dicts[span]['logs'] = [log for log in relevant_logs if Span_to_datetime(span, dicts[span]['goals'])[0] <= pytz.utc.localize(log.created_at) and pytz.utc.localize(log.created_at) <= Span_to_datetime(span, dicts[span]['goals'])[1]]

    return dicts

def span_to_text(span, end_date):
    #match doesn't work on 3.8.10
    now = datetime.now()
    if span == 'DAILY' or span == 'DAY':
        return 'untill end of Day'
    if span == 'DATE':
        # e.x 28th Jan 2024
        return "untill " + datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f%z").strftime("{0} %b %Y").format(ordinal(datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f%z").day)) + " [DATE]"
    if span == 'WEEKLY':
        if now.replace(tzinfo=pytz.UTC) < datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f%z"):
            return 'untill end of Week'
        else:
            return "untill " + Span_to_datetime(Span("WEEKLY"), [end_date])[1].strftime("{0} %b %Y").format(ordinal(Span_to_datetime(Span("WEEKLY"), [end_date])[1].day)) + " [WEEKLY]"
    if span == 'MONTHLY':
        if now.replace(tzinfo=pytz.UTC) < datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f%z"):
            return 'untill end of Month'
        else:
            return "untill " + Span_to_datetime(Span("MONTHLY"), [end_date])[1].strftime("{0} %b %Y").format(ordinal(Span_to_datetime(Span("MONTHLY"), [end_date])[1].day)) + " [MONTHLY]"



# def goal_algo(dict, log_bool, store, interaction, media_type):
#     goals_description = []
#     goal_message = []
#     for goals_row in dict["goals"]:
#         until_text = span_to_text(goals_row.span, goals_row.end)
#         if bool(dict['logs']):
#             points = []
#             for log in dict['logs']:
#                 if goals_row.goal_type == "SPECIFIC" and goals_row.text == log.title and goals_row.media_type == log.media_type:
#                     points.append(log.amount)
#                 elif goals_row.media_type == log.media_type:
#                     if goals_row.goal_type == "MEDIA":
#                         points.append(log.amount)
#                     if goals_row.goal_type == "POINTS":
#                         points.append(_to_amount(log.media_type.value, log.amount))
#                 elif goals_row.media_type.value == "ANYTHING":
#                     points.append(_to_amount(log.media_type.value, log.amount))
#             points = sum(points)
#             if points >= goals_row.amount:
#                 goals_description.append(f"""- ~~{round(points, 2)}/{goals_row.amount} {media_type_format(goals_row.media_type.value)} {get_name_of_immersion(goals_row.media_type.value, goals_row.text)[2]} ({until_text})~~""")
#                 if log_bool and not store.goal_already_completed_before(interaction.user.id, goals_row.span, goals_row.media_type, goals_row.text):
#                         goal_message.append((interaction.user.mention, media_type_grammer(media_type.upper()), goals_row.amount, media_type_format(media_type.upper()), get_name_of_immersion(goals_row.media_type.value, goals_row.text)[1], random_emoji()))
#                         store.goal_completed(interaction.user.id, goals_row.span, goals_row.amount, goals_row.media_type, goals_row.text)
#             else:
#                 goals_description.append(f"""- {round(points, 2)}/{goals_row.amount} {media_type_format(goals_row.media_type.value)} {get_name_of_immersion(goals_row.media_type.value, goals_row.text)[2]} ({until_text})""")
#         else:
#             goals_description.append(f"""- 0/{goals_row.amount} {media_type_format(goals_row.media_type.value)} {get_name_of_immersion(goals_row.media_type.value, goals_row.text)[2]} ({until_text})""")

#     return goals_description, goal_message

# def get_goal_description(logs, goals, log_bool, store, interaction, media_type):
#     goals_description = []
#     goal_message = []
#     for goals_row in goals:
#         until_text = span_to_text(goals_row.span, goals_row.end)
#         if bool(logs):
#             points = []
#             for log in logs:
#                 if goals_row.goal_type == "SPECIFIC" and goals_row.text == log.title and goals_row.media_type == log.media_type:
#                     points.append(log.amount)
#                 elif goals_row.media_type == log.media_type:
#                     if goals_row.goal_type == "MEDIA":
#                         points.append(log.amount)
#                     if goals_row.goal_type == "POINTS":
#                         points.append(_to_amount(log.media_type.value, log.amount))
#                 elif goals_row.media_type.value == "ANYTHING":
#                     points.append(_to_amount(log.media_type.value, log.amount))
#             points = sum(points)
#             if points >= goals_row.amount:
#                 goals_description.append(f"""- ~~{round(points, 2)}/{goals_row.amount} {media_type_format(goals_row.media_type.value)} {get_name_of_immersion(goals_row.media_type.value, goals_row.text)[2]} ({until_text})~~""")
#                 if log_bool and not store.goal_already_completed_before(interaction.user.id, goals_row.span, goals_row.media_type, goals_row.text):
#                         goal_message.append((interaction.user.mention, media_type_grammer(media_type.upper()), goals_row.amount, media_type_format(media_type.upper()), get_name_of_immersion(goals_row.media_type.value, goals_row.text)[1], random_emoji()))
#                         store.goal_completed(interaction.user.id, goals_row.span, goals_row.amount, goals_row.media_type, goals_row.text)
#             else:
#                 goals_description.append(f"""- {round(points, 2)}/{goals_row.amount} {media_type_format(goals_row.media_type.value)} {get_name_of_immersion(goals_row.media_type.value, goals_row.text)[2]} ({until_text})""")
#         else:
#             goals_description.append(f"""- 0/{goals_row.amount} {media_type_format(goals_row.media_type.value)} {get_name_of_immersion(goals_row.media_type.value, goals_row.text)[2]} ({until_text})""")

#     goals_description = '\n'.join(goals_description)

#     return goals_description, goal_message
    # goals_description = []
    # goal_message = []

    # for span in Span:
    #     description, message = goal_algo(dict=dicts[span], log_bool=log_bool, store=store, interaction=interaction, media_type=media_type)
    #     goals_description += description
    #     goal_message  += message

    # goals_description  = '\n'.join(goals_description)

    # return goals_description, goal_message
from modals.goal import Goal

def undo_goal(goals, log, store_goal, MULTIPLIERS):
    for goals_row in goals:
        list = []
        if goals_row.amount <= goals_row.current_amount:
            continue
        if goals_row.goal_type == "SPECIFIC" and goals_row.text == log.note and goals_row.media_type.value == log.media_type.upper():
            list.append(log.amount)
        elif goals_row.media_type.value == log.media_type.upper() and goals_row.goal_type != "SPECIFIC":
            if goals_row.goal_type == "MEDIA":
                list.append(log.amount)
            elif goals_row.goal_type == "POINTS":
                list.append(_to_amount(log.media_type, log.amount, MULTIPLIERS))
        elif goals_row.media_type.value == "ANYTHING":
            list.append(_to_amount(log.media_type.upper(), log.amount, MULTIPLIERS))
        points = sum(list)
        goal = Goal(goals_row.discord_user_id, goals_row.goal_type, goals_row.media_type, goals_row.current_amount, goals_row.amount, goals_row.text, goals_row.span, goals_row.created_at, goals_row.end)
        store_goal.update_amount(goal, goals_row.current_amount-points)
        if goals_row.amount == goals_row.current_amount:
            store_goal.search_completed(goals_row)

def update_goals(interaction, goals, log, store_goal, media_type, MULTIPLIERS, codes, file_path):
    goals_to_update = []
    goal_message = []
    for goals_row in goals:
        if goals_row.media_type.value == "LISTENING" and goals_row.goal_type == "SPECIFIC":
            goals_row_text = goals_row.text.replace("''", "'")
        else:
            goals_row_text = goals_row.text
        list = []
        if goals_row.amount <= goals_row.current_amount:
            continue
        if goals_row.goal_type == "SPECIFIC" and goals_row_text == log.title and goals_row.media_type.value == log.media_type.upper():
            list.append(log.amount)
        elif goals_row.media_type.value == log.media_type.upper() and goals_row.goal_type != "SPECIFIC":
            if goals_row.goal_type == "MEDIA":
                list.append(log.amount)
            elif goals_row.goal_type == "POINTS":
                list.append(_to_amount(log.media_type.upper(), log.amount, MULTIPLIERS))
        elif goals_row.media_type.value == "ANYTHING":
            list.append(_to_amount(log.media_type.upper(), log.amount, MULTIPLIERS))
        points = sum(list)
        goals_to_update.append(Goal(log.duid, goals_row.goal_type, goals_row.media_type, goals_row.current_amount + round(points, 2), goals_row.amount, goals_row_text, goals_row.span, goals_row.created_at, goals_row.end))
        if goals_row.amount == goals_row.current_amount + round(points, 2) and not store_goal.goal_already_completed_before(interaction.user.id, goals_row.span, goals_row.media_type, goals_row_text):
            goal_message.append((interaction.user.mention, media_type_grammer(media_type.upper()), goals_row.amount, media_type_format(media_type.upper()), get_name_of_immersion(goals_row.media_type.value, goals_row_text, codes, file_path)[1], random_emoji()))
            store_goal.goal_completed(interaction.user.id, goals_row.span, goals_row.amount, goals_row.media_type, goals_row_text)

    for goal in goals_to_update:
        store_goal.update_amount(goal, goal.current_amount)

    return goal_message

def get_goal_description(goals, codes_path, codes):
    goals_description = []
    for goal_row in goals:
        try:
            updated_date = f'<t:{int(datetime.strptime(goal_row.end, "%Y-%m-%d %H:%M:%S.%f%z").timestamp())}:R>'
        except Exception:
            updated_date = goal_row.end
        goal_title = get_name_of_immersion(goal_row.media_type.value, goal_row.text, codes, codes_path)
        if goal_row.current_amount < goal_row.amount:
                goals_description.append(f"""- {round(goal_row.current_amount, 2)}/{goal_row.amount} {media_type_format(goal_row.media_type.value) if goal_row.goal_type != "POINTS" else "points"} of [{goal_title[1]}]({goal_title[2]}) ({updated_date})""")
        else:
            goals_description.append(f"""~~- {round(goal_row.current_amount, 2)}/{goal_row.amount} {media_type_format(goal_row.media_type.value) if goal_row.goal_type != "POINTS" else "points"} of [{goal_title[1]}]({goal_title[2]}) ({updated_date})~~""")

    return goals_description

from modals.amount import Amount as AMOUNT
def amount_time_conversion(media_type, amount):
    #converts raw string to (int) time e.x "2:30" to (min) 150
    if (media_type == "Listening" or media_type == "Readtime") and ":" in amount:
        try:
            time = amount.split(":")
            if len(time) == 1:
                min = time
                return AMOUNT(True, min)
            elif len(time) == 2:
                if len(time[0]) > 2 or len(time[1]) > 2:
                    return AMOUNT(False, 0)
                min, sec = time
                return AMOUNT(True, (int(min)) + (int(sec) / 60))
            elif len(time) == 3:
                if len(time[0]) > 2 or len(time[1]) > 2 or len(time[2]) > 2:
                    return AMOUNT(False, 0)
                hours, min, sec = time
                return AMOUNT(True, (int(hours) * 60) + (int(min)) + (int(sec) / 60))
            else:
                return AMOUNT(False, 0)
        except Exception:
            return AMOUNT(False, 0)
    else:
        try:
            amount = int(amount)
        except Exception:
            return AMOUNT(False, 0)

    return AMOUNT(True, amount)
            
#calculates current achievemnt rank and next achievement rank
#returns milestone, emoji, name of current achievement rank
#and of next achievement rank for final log text message
def check_achievements(discord_user_id, media_type, store_prod, MULTIPLIERS):
    logs = store_prod.get_logs_by_user(discord_user_id, media_type, None, None)
    weighed_points_mediums = multiplied_points(logs, MULTIPLIERS)
    abmt = calc_achievements(weighed_points_mediums)
    if not bool(abmt):
        return 0, 0, 0, "", "", "", "", 0
    lower_interval, current_points, upper_interval, rank_emoji, rank_name, next_rank_emoji, next_rank_name, rank_id = get_achievemnt_index(abmt)
    
    return lower_interval, current_points, upper_interval, rank_emoji, rank_name, next_rank_emoji, next_rank_name, rank_id

import json
def _to_amount(media_type, amount, MULTIPLIERS):
    return amount * MULTIPLIERS[media_type]

#returns dict with total amount of points for each media_type
#points are weighted via MULTIPLIERS
def multiplied_points(logs, MULTIPLIERS):
    dictes = defaultdict(list)
    for row in logs:
        dictes[row.media_type.value].append(row.amount)
    return dict([(key, (_to_amount(key, sum(values), MULTIPLIERS), sum(values))) for key, values in dictes.items()])

def media_type_format(media_type):
    if media_type == "BOOK":
        return "pgs"
    elif media_type == "MANGA":
        return "pgs"
    elif media_type == "VN":
        return "chrs"
    elif media_type == "ANIME":
        return "eps"
    elif media_type == "LISTENING":
        return "mins"
    elif media_type == "READING":
        return "chrs"
    elif media_type == "READTIME":
        return "mins"
    elif media_type == "ANYTHING":
        return "anything"
    elif media_type == "OUTPUT":
        return "chars"
    else:
        raise Exception(f'Unknown media type: {media_type}')
    
def media_type_grammer(media_type):
    if media_type == "BOOK":
        return "reading"
    elif media_type == "MANGA":
        return "reading"
    elif media_type == "VN":
        return "reading"
    elif media_type == "ANIME":
        return "watching"
    elif media_type == "LISTENING":
        return "listening"
    elif media_type == "READING":
        return "reading"
    elif media_type == "READTIME":
        return "reading"
    else:
        raise Exception(f'Unknown media type: {media_type}')
    
    
millnames = ['','k','m','b']

def millify(n):
    n = float(n)
    if n == float('inf'):
        return 'inf'
    if n < 10_000:
        return f'{n:,g}'
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    return '{:.2f}{}'.format(n / 10**(3 * millidx), millnames[millidx])

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def calc_achievements(amount_by_media_type):
    abmt = amount_by_media_type
    # Combine Book and Reading
    if MediaType.BOOK in abmt or MediaType.READING in abmt:
        abmt[MediaType.BOOK] = abmt.get(MediaType.BOOK, 0) + abmt.get(MediaType.READING, 0) / 350.0
        abmt.pop(MediaType.READING, None)
    return abmt

#magic idk didnt write it myself lol ¯\_(ツ)_/¯
def get_achievemnt_index(abmt):
    for media_type, amount in abmt.items():
        index = get_index_by_ranges(amount[1], ACHIEVEMENTS[media_type])
        #fix inline logic
        return ACHIEVEMENTS[media_type][index], amount[1], ACHIEVEMENTS[media_type][index+1] if index != 7 else ACHIEVEMENTS[media_type][index], ACHIEVEMENT_EMOJIS[index], ACHIEVEMENT_RANKS[index], ACHIEVEMENT_EMOJIS[index+1]  if index != 7 else ACHIEVEMENT_EMOJIS[index], ACHIEVEMENT_RANKS[index+1] if index != 7 else ACHIEVEMENT_RANKS[index], ACHIEVEMENT_IDS[index]

def get_index_by_ranges(amount, ranges):

    # if amount < ranges[0]:
    #     return 0
    for i, (lower, upper) in enumerate(pairwise(ranges)):
        if lower <= amount < upper:
            return i
    else:
        return -1

def get_achievement_text(abmt):
    # Media specific achievements
    achievements = []
    for media_type, amount in abmt.items():
        index = get_index_by_ranges(amount[1], ACHIEVEMENTS[media_type])
        achievement = (f'{ACHIEVEMENT_EMOJIS[index]} {media_type.title()} {ACHIEVEMENT_RANKS[index]}: {millify(amount[1])} ({millify(ACHIEVEMENTS[media_type][index])} - {ACHIEVEMENTS[media_type][index+1]} {media_type_format(media_type)})')
        achievements.append(achievement)


    # Point specific achievements
    total_points = sum(amount[0] for media_type, amount in abmt.items())
    index = get_index_by_ranges(total_points, PT_ACHIEVEMENTS)
    immersion_achievement = (
        f'{ACHIEVEMENT_EMOJIS[index]} Immersion {ACHIEVEMENT_RANKS[index]}: {total_points:,g} '
        f'({PT_ACHIEVEMENTS[index]:,} - {PT_ACHIEVEMENTS[index+1]:,} pts)'
    )
    achievements.append(immersion_achievement)

    return achievements

def ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return str(number) + suffix

def get_cover(media_type, name):
    if name and name.startswith("v"):
        vndb = VNDB()
        vns = vndb.get_vn(VN.id == name[1:])
        try:
            vn = vns[0]
        except Exception:
            return None
        
        return vn.image
    
    elif name and name.isdigit():
        anilist = Anilist()
        try:
            if media_type.upper() == "MANGA":
                return anilist.get_manga_with_id(name)["cover_image"]
            #depending on the anime name_english might not work but it looks cleaner with so im including it
            elif media_type.upper() == "ANIME":
                return anilist.get_anime_with_id(name)["cover_image"]
        except Exception:
            return None
    
    return None

#bits and parts for final log message like point unit (chars, pgs, etc)
#points conversion (1/350 points/characters → x points)
#name of the log immersion via anilist or vndb

def get_name_of_immersion(media_type, name, codes, file_path):
    if name in codes.keys():
        medium = codes[name]
        if name.startswith("v") and name[1].isdigit():
            return f'VNDB: [{medium[0]}]({medium[1]})', medium[0], medium[1], medium[2]
        elif name.isdigit():
            return f'Anilist: [{medium[0]}]({medium[1]})', medium[0], medium[1], medium[2]
        else:
            return f'TMDB: [{medium[0]}]({medium[1]})', medium[0], medium[1], medium[2]
    
    def not_found():
        return f"{media_type}"
    
    if name and name.startswith("v") and media_type == "VN":
        vndb = VNDB()
        vns = vndb.get_vn(VN.id == name[1:])
        try:
            vn = vns[0]
        except Exception:
            return not_found(), name
        if name not in codes.keys():
            codes[name] = [vn.title, f"<https://vndb.org/{name}>", vn.image]
            with open(file_path, "w") as file:
                json.dump(codes, file)
        return f'VNDB: [{vn.title}](https://vndb.org/{name})',vn.title, f"<https://vndb.org/{name}>", vn.image
    
    elif name and name.isdigit() and (media_type == "ANIME" or media_type == "MANGA"):
        anilist = Anilist()
        try:
            if media_type == "MANGA":
                manga_info = anilist.get_manga_with_id(name)
                updated_title = manga_info["name_english"].replace(" ", "-")
                if name not in codes.keys():
                    codes[name] = [manga_info["name_english"], f'https://anilist.co/manga/{name}/{updated_title}/', manga_info["cover_image"]]
                    with open(file_path, "w") as file:
                        json.dump(codes, file)
                return f'Anilist: [{manga_info["name_english"]}](https://anilist.co/manga/{name}/{updated_title}/)', manga_info["name_english"], f'https://anilist.co/manga/{name}/{updated_title}/', manga_info["cover_image"]
            #depending on the anime name_english might not work but it looks cleaner with so im including it
            elif media_type == "ANIME":
                try:
                    anime_info = anilist.get_anime_with_id(name)
                    updated_title = anime_info["name_english"].replace(" ", "-")
                except Exception:
                    updated_title = anime_info["name_romaji"].replace(" ", "-")
                    if name not in codes.keys():
                        codes[name] = [updated_title, f'https://anilist.co/anime/{name}/{updated_title}/', anime_info["cover_image"]]
                        with open(file_path, "w") as file:
                            json.dump(codes, file)
                    return f'Anilist: [{updated_title}](https://anilist.co/anime/{name}/{updated_title}/)', updated_title, f'https://anilist.co/anime/{name}/{updated_title}/', anime_info["cover_image"]
                    
                else:
                    if name not in codes.keys():
                        codes[name] = [anime_info["name_english"], f'https://anilist.co/anime/{name}/{updated_title}/', anime_info["cover_image"]]
                        with open(file_path, "w") as file:
                            json.dump(codes, file)
                    return f'Anilist: [{anime_info["name_english"]}](https://anilist.co/anime/{name}/{updated_title}/)', anime_info["name_english"], f'https://anilist.co/anime/{name}/{updated_title}/', anime_info["cover_image"]
        except Exception:
            return "Source: N/A", f"{name}", "https://anilist.co/home", None
    elif name and media_type == 'LISTENING':
        name = eval(name)
        tmdb = tmdbv3api.TMDb()
        tmdb.api_key = 'API_KEY_HERE'
        tmdb.REQUESTS_SESSION = requests.Session()
        
        try:
            media_id = name[0]
            media_type = name[1]
            media_image = name[2]

            if media_type == "movie":
                movie = tmdbv3api.Movie()
                response = movie.details(media_id)
                media_type = "movie"
            else:
                tv = tmdbv3api.TV()
                response = tv.details(media_id)
                media_type = "tv"

            media_url = f"https://www.themoviedb.org/{media_type}/{media_id}"

            title = response.get('name') or response.get('title')
            image_url = f"https://image.tmdb.org/t/p/original{media_image}"

            if media_id not in codes.keys():
                codes[media_id] = [title, media_url, image_url]
                with open(file_path, "w") as file:
                    json.dump(codes, file)

            return f"TMDB: [{title}]({media_url})", title, media_url, image_url
        
        except Exception as e:
            print(f"Error fetching media info: {e}")
            return None
        
    elif name:
        return "Source: N/A", f"{name}", "https://anilist.co/home", None
    
    return "Source: N/A", f"{not_found()}", "https://anilist.co/home", None

from fractions import Fraction
def point_message_converter(media_type, amount, name, MULTIPLIERS, codes, file_path):
        
    if media_type == "VN":
        try:
            conversion = Fraction(MULTIPLIERS[media_type]).limit_denominator()
        except Exception:
            conversion = MULTIPLIERS[media_type]
        return _to_amount(media_type, amount, MULTIPLIERS), "chars", f"{conversion} points/characters → +{round(_to_amount(media_type, amount, MULTIPLIERS),4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    elif media_type == "MANGA":
        return _to_amount(media_type, amount, MULTIPLIERS), "pgs", f"{MULTIPLIERS[media_type]} points per page → +{round(_to_amount(media_type, amount, MULTIPLIERS), 4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    
    elif media_type == "BOOK":
        return _to_amount(media_type, amount, MULTIPLIERS), "pgs", f"{MULTIPLIERS[media_type]} point per page → +{round(_to_amount(media_type, amount, MULTIPLIERS), 4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    
    elif media_type == "ANIME":
        return _to_amount(media_type, amount, MULTIPLIERS), "eps", f"{MULTIPLIERS[media_type]} points per eps → +{round(_to_amount(media_type, amount, MULTIPLIERS), 4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    
    elif media_type == "READING":
        try:
            conversion = Fraction(MULTIPLIERS[media_type]).limit_denominator()
        except Exception:
            conversion = MULTIPLIERS[media_type]
        return _to_amount(media_type, amount, MULTIPLIERS), "chars", f"{conversion} points/character of reading → +{round(_to_amount(media_type, amount, MULTIPLIERS), 4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    
    elif media_type == "READTIME":
        return _to_amount(media_type, amount, MULTIPLIERS), "mins", f"{MULTIPLIERS[media_type]} points/min of readtime → +{round(_to_amount(media_type, amount, MULTIPLIERS), 4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    
    if media_type == "LISTENING":
        return _to_amount(media_type, amount, MULTIPLIERS), "mins", f"{MULTIPLIERS[media_type]} points/min of listening → +{round(_to_amount(media_type, amount, MULTIPLIERS),4)} points", get_name_of_immersion(media_type, name, codes, file_path)
    
def start_end_tf(now, timeframe):
    if timeframe == "Weekly":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        title = f"""{now.year}'s {timeframe} Leaderboard"""
        
    if timeframe == "Monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (now.replace(day=28) + timedelta(days=4)) - timedelta(days=(now.replace(day=28) + timedelta(days=4)).day)
        title = f"""Monthly ({now.strftime("%B")} {now.year}) Leaderboard"""
        
    if timeframe == "All Time":
        start = datetime(year=2021, month=3, day=4, hour=0, minute=0, second=0, microsecond=0)
        end = now
        title = f"""All time Leaderboard till {now.strftime("%B")} {now.year}"""
    
    if timeframe == "Yearly":
        start = now.date().replace(month=1, day=1)
        end = now.date().replace(month=12, day=31)
        title = f"{now.year}'s Leaderboard"

    return now, start, end, title

def make_ordinal(n):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return f'{n}{suffix}'

def get_emoji(user_id, amount, title):
    today = datetime.today()
    if any(substring in title for substring in JACK_FILTER):
        return f'<:KimoiHuh:931588710473031761>'
    elif today.month == 10 and today.day == 3:
        return '🕓'
    elif amount == 1:
        return f'<:ChubbyGero:831348462305673286>'
    else:
        return random_emoji()

def emoji(s):
    return f'<:{s}:{EMOJI_TABLE[s]}>'

def random_emoji():
    return emoji(random.choice(list(EMOJI_TABLE)))

def indices_media(lst, goals_row, interaction):
    # if goal_freq == "Daily":
    #     [i for i, x in enumerate([b for b in lst if interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) < x.created_at < interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)]) if x.media_type == item]
    # else:
    #     [i for i, x in enumerate([b for b in lst if interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) < x.created_at < goal_freq]) if x.media_type == item]
    if goals_row.freq == "Daily":
        return [i for i, x in enumerate(lst) if x.media_type == goals_row.media_type and interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) < x.created_at < interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)]
    else:
        return [i for i, x in enumerate(lst) if x.media_type == goals_row.media_type and goals_row.created_at < x.created_at < goals_row.freq]

def indices_text(lst, goals_row, interaction):
    if goals_row.freq == "Daily":
        return [i for i, x in enumerate(lst) if (x.note.strip('][').split(', '))[0].replace("'", "") == goals_row.text and interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) < x.created_at < interaction.created_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)]
    else:
        return [i for i, x in enumerate(lst) if (x.note.strip('][').split(', '))[0].replace("'", "") == goals_row.text] #and goals_row.created_at < x.created_at < goals_row.freq]
    
# def get_roles(guild):
#     roles = [f for k in ACHIEVEMENT_RANKS if (f := get(guild.roles, name=k))]
#     if len(roles) != len(ACHIEVEMENT_RANKS):
#         return {}
#     return dict(zip(ACHIEVEMENT_RANKS, roles))
