import sqlite3
from collections import namedtuple
from enum import Enum
from modals.maintenance import Maintenance as m


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
    OUTPUT = 'OUTPUT'

def namedtuple_factory(cursor, row):
    """Returns sqlite rows as named tuples."""
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    res = Row(*row)
    # HACK:
    if hasattr(res, 'media_type'):
        return res._replace(media_type=MediaType[res.media_type])
    return res

class UserSettings:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = namedtuple_factory

    def fetch(self, query):
        # print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    
    def register_user(self, discord_user_id, timezone):
        with self.conn:
            self.conn.execute("INSERT INTO users (discord_user_id, timezone)VALUES (?,?)", (int(discord_user_id), str(timezone)))
            self.conn.commit()

    def check_existing_user(self, discord_user_id):
        query = f"""SELECT EXISTS(
            SELECT * FROM users WHERE discord_user_id=?
            ) AS didTry"""
        cursor = self.conn.cursor()
        cursor.execute(query, [discord_user_id])
        return cursor.fetchall()[0][0] == 1

class Debug:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = namedtuple_factory

    def fetch(self, query):
        # print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    
    def start_maintenance(self, discord_user_id, maintenance_msg):
        with self.conn:
            self.conn.execute("INSERT INTO debug (discord_user_id, maintenance_msg) VALUES (?,?)", (int(discord_user_id), str(maintenance_msg)))
            self.conn.commit()
    
    def end_maintenance(self):
        with self.conn:
            self.conn.execute("DELETE FROM debug")
            self.conn.commit()

    def check_maintenance(self):
        query = f"""SELECT EXISTS(
            SELECT * FROM debug
            ) AS didTry"""
        cursor = self.conn.cursor()
        cursor.execute(query)
        bool = cursor.fetchall()[0][0] == 1
        if bool:
            query = f"""SELECT maintenance_msg FROM debug"""
            cursor = self.conn.cursor()
            cursor.execute(query)
            message = cursor.fetchall()[0]
        else:
            message = ""
        return m(bool, message)

class Store:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = namedtuple_factory
    
    def fetch(self, query):
        # print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def new_log(
        self, discord_guild_id, discord_user_id, media_type, amount, title, note, created_at
    ):
        with self.conn:
            self.conn.execute("INSERT INTO logs (discord_guild_id, discord_user_id, media_type, amount, title, note, created_at)VALUES (?,?,?,?,?,?,?)", (int(discord_guild_id), int(discord_user_id), str(media_type), int(amount), str(title), str(note), created_at))
            self.conn.commit()
            
    def current_points(self, discord_guild_id, discord_user_id, created_at):
        with self.conn:
            query = f"""
            SELECT SUM(amount) as sum_amount FROM logs
            WHERE discord_guild_id={discord_user_id} AND created_at BETWEEN '{created_at[0]}' AND '{created_at[1]}'
            """
        
            return self.fetch(query)
        
    def get_leaderboard(self, discord_user_id, timeframe, media_type, MULTIPLIERS):
        with self.conn:
            print(len(timeframe))
            if media_type:
                where_clause = f"WHERE media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
            else:
                where_clause = f"WHERE created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
            
            query = f"""
            WITH scoreboard AS (
                SELECT
                    discord_user_id,
                    SUM(
                    CASE
                        WHEN media_type = 'BOOK' THEN amount * {MULTIPLIERS['BOOK']}
                        WHEN media_type = 'MANGA' THEN amount * {MULTIPLIERS['MANGA']}
                        WHEN media_type = 'VN' THEN amount * {MULTIPLIERS['VN']}
                        WHEN media_type = 'ANIME' THEN amount * {MULTIPLIERS['ANIME']}
                        WHEN media_type = 'READING' THEN amount * {MULTIPLIERS['READING']}
                        WHEN media_type = 'READTIME' THEN amount * {MULTIPLIERS['READTIME']}
                        WHEN media_type = 'LISTENING' THEN amount * {MULTIPLIERS['LISTENING']}
                        ELSE 0
                    END
                    ) AS total
                FROM logs
                {where_clause}
                GROUP BY discord_user_id
                ), leaderboard AS (
                SELECT
                    discord_user_id,
                    total,
                    RANK () OVER (ORDER BY total DESC) AS rank
                FROM scoreboard
                )
                SELECT * FROM leaderboard
                WHERE (
                rank <= 20
                ) OR (
                rank >= (SELECT rank FROM leaderboard WHERE discord_user_id = {discord_user_id}) - 1
                AND
                rank <= (SELECT rank FROM leaderboard WHERE discord_user_id = {discord_user_id}) + 1
                );
            """
            return self.fetch(query)
    
    def get_logs_by_user_with_row_id(self, discord_user_id, media_type, timeframe, name):
        #refractor later
        if media_type == None and timeframe == None and name == None:
            where_clause = f"discord_user_id={discord_user_id}"
        if media_type and media_type != None and timeframe  and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif not media_type and media_type != None and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe == None  and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}'"""
        elif media_type == None and timeframe and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type == None and timeframe and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe and name:
            title = name
            where_clause = f"discord_user_id={discord_user_id} AND title='{title}' AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif timeframe and name:
            title = name
            where_clause = f"discord_user_id={discord_user_id} AND title='{title}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif timeframe:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
            
        query = f"""
        SELECT rowid, * FROM logs
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)
    
    def get_logs_by_user(self, discord_user_id, media_type, timeframe, name):
        #refractor later
        if media_type == None and timeframe == None and name == None:
            where_clause = f"discord_user_id={discord_user_id}"
        if media_type and media_type != None and timeframe  and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif not media_type and media_type != None and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe == None  and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}'"""
        elif media_type == None and timeframe and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type == None and timeframe and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe and name == None:
            where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif media_type and timeframe and name:
            title = name
            where_clause = f"discord_user_id={discord_user_id} AND title='{title}' AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif timeframe and name:
            title = name
            where_clause = f"discord_user_id={discord_user_id} AND title='{title}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        elif timeframe:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
            
        query = f"""
        SELECT * FROM logs
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)
    
    def get_that_log(self, discord_user_id):
        where_clause = f'''discord_user_id={discord_user_id}'''
        query = f"""SELECT * FROM logs WHERE {where_clause} ORDER BY created_at DESC"""
        
        return self.fetch(query)[0]
        
    def delete_log(self, rowId):
        where_clause = f"""
        WHERE rowid={rowId}
        """
        print(where_clause)
        query = f"""
        DELETE FROM logs {where_clause}"""
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()

    def get_goal_relevant_logs(self, discord_user_id, beginn, end):
        where_clause = f"""discord_user_id={discord_user_id} AND created_at BETWEEN '{beginn}' AND '{end}'"""
    
        query = f"""SELECT media_type, SUM(amount) as amount, note, created_at FROM logs
        WHERE {where_clause}
        GROUP BY media_type, note
        ORDER BY created_at DESC
        """
        
        return self.fetch(query)
        
    def get_log_streak(self, discord_user_id):
        query = f"""WITH ranked_logs AS (
  SELECT
    discord_user_id,
    DATE(created_at) as created_at,
    RANK() OVER (PARTITION BY discord_user_id ORDER BY created_at) AS log_rank
  FROM
    logs WHERE discord_user_id = {discord_user_id}
  GROUP BY
    discord_user_id, DATE(created_at)
),
streaks AS (
  SELECT
    discord_user_id,
    DATE(created_at, '-' || log_rank || ' days') AS streak_group,
    COUNT(*) streak,
    MIN(created_at) started_on,
    MAX(created_at) ended_on
  FROM
    ranked_logs
  GROUP BY
    discord_user_id,
    streak_group
),
current_streaks AS (
  SELECT
    discord_user_id,
    streak,
    started_on,
    ended_on
  FROM
    streaks
  WHERE
    ended_on = DATE('now')
)
SELECT
  streaks.discord_user_id,
  streaks.started_on AS longest_streak_started_on,
  streaks.ended_on AS longest_streak_ended_on,
  MAX(streaks.streak) AS longest_streak,
  current_streaks.started_on AS current_streak_started_on,
  current_streaks.ended_on AS current_streak_ended_on,
  current_streaks.streak AS current_streak
FROM
  streaks
LEFT JOIN
  current_streaks ON current_streaks.discord_user_id = streaks.discord_user_id
GROUP BY
  streaks.discord_user_id;"""
        
        return self.fetch(query)

    def get_longest_streak(self, discord_user_id):
        query = f"""SELECT discord_user_id, max(created_at) as ends_at, count(*) as streak
        FROM (SELECT *, date(created_at, -(row_number() OVER (PARTITION BY discord_user_id)) || ' days') 
        as base_date
        FROM (SELECT DISTINCT date(created_at, '0 days') as created_at, discord_user_id
        FROM logs WHERE discord_user_id={discord_user_id}
        ORDER BY created_at) as points) as points
        ORDER BY streak DESC
        """
        
        return self.fetch(query)
        # query = f"""
        # with cte as (
        # select discord_user_id, date(created_at) as created_at
        # from logs WHERE discord_user_id={discord_user_id}
        # group by discord_user_id, date(created_at)
        # ),
        # cte2 as (
        # select *, julianday(created_at) - julianday(lag(created_at) over (partition by discord_user_id order by created_at)) as date_diff
        # from cte 
        # ),
        # cte3 as (
        # select *, SUM(CASE WHEN date_diff = 1 THEN 0 ELSE 1 END) OVER (partition by discord_user_id order by created_at) AS grp 
        # from cte2
        # ),
        # cte4 as (
        # select discord_user_id, count(1) as period_length
        # from cte3
        # group by discord_user_id, grp
        # )
        # select discord_user_id, max(period_length) as longest_period
        # from cte4
        # group by discord_user_id"""
#         query = f"""
#         with user_date_combos as (
#     select distinct
#            discord_guild_id,
#            date(created_at) as created_date
#       from logs WHERE discord_guild_id={discord_user_id}
# ),
# consecutive_grouping AS (
#     SELECT
#       discord_guild_id,
#       created_date,
#       created_date - cast(ROW_NUMBER() OVER (
#         partition by discord_guild_id
#             ORDER BY created_date) as int) + 1 as start_of_streak
#     FROM user_date_combos
#   )
# select discord_guild_id,
#        max(length_of_streak) as longest_streak
#   from (
#        select discord_guild_id,
#               start_of_streak,
#               count(1) as length_of_streak
#          from consecutive_grouping
#         group
#            by discord_guild_id,
#               start_of_streak) as tmp
#  group
#     by discord_guild_id"""
#         query = f"""WITH
 
#   -- This table contains all the distinct date 
#   -- instances in the data set
#   dates(date) AS (
#     SELECT DISTINCT CAST(created_at AS DATE)
#     FROM logs
#     WHERE discord_user_id={discord_user_id}
#   ),
   
#   -- Generate "groups" of dates by subtracting the
#   -- date's row number (no gaps) from the date itself
#   -- (with potential gaps). Whenever there is a gap,
#   -- there will be a new group
#   groups AS (
#     SELECT
#       ROW_NUMBER() OVER (ORDER BY date) AS rn,
#       dateadd(day, -ROW_NUMBER() OVER (ORDER BY date), date) AS grp,
#       date
#     FROM dates
#   )
# SELECT
#   COUNT(*) AS consecutiveDates,
#   MIN(date) AS minDate,
#   MAX(date) AS maxDate
# FROM groups
# GROUP BY grp
# ORDER BY 1 DESC, 2 DESC"""
        # query = f"""SELECT DISTINCT 
        # discord_guild_id, created_at RANK() OVER(PARTITION BY discord_user_id ORDER BY created_at) rank 
        # FROM logs WHERE discord_user_id={discord_user_id}"""

class Set_jp:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = namedtuple_factory

    def fetch(self, query):
        # print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def all_output(self):
        query = """SELECT channel_id, SUM(amount) AS total_amount
        FROM jp
        GROUP BY channel_id;"""
        return self.fetch(query)
        
    def delete_output(self, msg_id):
        where_clause = f"message_id={msg_id}"
        query = f"""DELETE FROM jp WHERE {where_clause}"""
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()
    
    def log_jp(self, discord_user_id, channel_id, msg_id, media_type, jp, amount, created_at):
        with self.conn:
            query = """
            INSERT INTO jp (discord_user_id, channel_id, message_id, media_type, japanese, amount, created_at)
            VALUES (?,?,?,?,?,?,?);
            """
            data = (discord_user_id, channel_id, msg_id, media_type, jp, amount, created_at)
            self.conn.execute(query, data)

    def get_jp(self, discord_user_id, timeframe):
        if timeframe == None:
            where_clause = f"discord_user_id={discord_user_id}"
        if timeframe:
            where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
        
        query = f"""SELECT * FROM jp
        WHERE {where_clause}
        ORDER BY created_at ASC;"""
        
        return self.fetch(query)
    
    def find_similar(self, discord_user_id, content):
        query = f"""SELECT EXISTS(
            SELECT * FROM jp WHERE discord_user_id=? AND japanese LIKE ?
            ) AS didTry"""
        cursor = self.conn.cursor()
        cursor.execute(query, [discord_user_id, content])
        return cursor.fetchall()[0][0] == 1
    
    def get_jp_leaderboard(self, discord_user_id, timeframe):
        with self.conn:
            where_clause = f"WHERE created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"""
            
            query = f"""
            WITH scoreboard AS (
                SELECT
                    discord_user_id,
                    SUM(
                    amount
                    ) AS total
                FROM jp
                {where_clause}
                GROUP BY discord_user_id
                ), leaderboard AS (
                SELECT
                    discord_user_id,
                    total,
                    RANK () OVER (ORDER BY total DESC) AS rank
                FROM scoreboard
                )
                SELECT * FROM leaderboard
                WHERE (
                rank <= 20
                ) OR (
                rank >= (SELECT rank FROM leaderboard WHERE discord_user_id = {discord_user_id}) - 1
                AND
                rank <= (SELECT rank FROM leaderboard WHERE discord_user_id = {discord_user_id}) + 1
                );
            """
            return self.fetch(query)

class Set_Goal:
    def __init__(self, db_name):
            self.conn = sqlite3.connect(
                db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.conn.row_factory = namedtuple_factory

    def fetch(self, query):
        # print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def new_goal(self, discord_user_id, goal_type, media_type, current_amount, amount, text, span, created_at, end):
        with self.conn:
            query = """
            INSERT INTO goals (discord_user_id, goal_type, media_type, current_amount, amount, text, span, created_at, end)
            VALUES (?,?,?,?,?,?,?,?,?);
            """
            data = (discord_user_id, goal_type, media_type, current_amount, amount, text, span, created_at, end)
            self.conn.execute(query, data)
            self.conn.commit()
            
    def get_goals(self, discord_user_id):
        where_clause = f"""discord_user_id={discord_user_id}"""
        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at ASC;
        """
        
        return self.fetch(query)
    
    
            
    def new_point_goal(self, discord_user_id, goal_type, media_type, current_amount, amount, text, span, created_at, end):
        with self.conn:
            query = """
            INSERT INTO goals (discord_user_id, goal_type, media_type, current_amount, amount, text, span, created_at, end)
            VALUES (?,?,?,?,?,?,?,?,?);
            """
            data = (discord_user_id, goal_type, media_type, current_amount, amount, text, span, created_at, end)
            self.conn.execute(query, data)
            self.conn.commit()
            
    def get_point_goals(self, discord_user_id, timeframe):
        where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
        query = f"""
        SELECT * FROM points
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)
    
    def get_goal_by_medium(self, discord_user_id, timeframe, media_type):
        where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
        query = f"""
        SELECT SUM(amount) as da FROM goals
        WHERE {where_clause};
        """
        
        return self.fetch(query)
            
    def get_daily_goals(self, discord_user_id):
        where_clause = f"discord_user_id={discord_user_id} and freq='Daily'"
        
        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)
    
    def get_date_goals(self, discord_user_id):
        where_clause = f"""discord_user_id={discord_user_id} AND span='DATE' ORDER BY created_at ASC"""

        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)[0]
    
    def check_goal_exists(self, discord_user_id, goal_type, span, media_type, text):
        cursor = self.conn.cursor()
        if text != None:
            query = f"""SELECT EXISTS(
            SELECT * FROM goals WHERE discord_user_id=? AND goal_type=? AND span=? AND media_type=? AND text LIKE ?
            ) AS didTry"""
            cursor.execute(query, [discord_user_id, goal_type, span, media_type, text])
        else:
            query = f"""SELECT EXISTS(
            SELECT * FROM goals WHERE discord_user_id=? AND goal_type=? AND span=? AND media_type=?
            ) AS didTry"""
            cursor.execute(query, [discord_user_id, goal_type, span, media_type])

        return cursor.fetchall()[0][0] == 1
    
    def goal_already_completed_before(self, discord_user_id, goal_type, media_type, text):
        # print(discord_user_id, goal_type, media_type, text)
        query = f"""SELECT EXISTS(
            SELECT * FROM completed WHERE discord_user_id=? AND goal_type=? AND media_type=? AND text LIKE ?
            ) AS didTry"""
        cursor = self.conn.cursor()
        cursor.execute(query, [discord_user_id, goal_type, media_type, text])
        return cursor.fetchall()[0][0] == 1
    
    def goal_completed(self, discord_user_id, goal_type, amount, media_type, text):
        with self.conn:
            query = """
            INSERT INTO completed (discord_user_id, goal_type, amount, media_type, text)
            VALUES (?,?,?,?,?);
            """
            # print(text)
            data = (discord_user_id, goal_type, amount, media_type, text)
            self.conn.execute(query, data)
    
    def get_all_goals(self):
        query = f"""
        SELECT * FROM goals
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)
    
    def get_all_completed(self):
        query = f"""
        SELECT * FROM goals
        ORDER BY created_at DESC;
        """
        
        return self.fetch(query)
    
    def delete_goal(self, discord_user_id, media_type, amount, span):
        where_clause = f"""discord_user_id={discord_user_id} AND media_type='{str(media_type).upper()}' AND amount={amount} AND span='{span}'"""
        query = f"""
        DELETE FROM goals WHERE {where_clause}"""
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()
        
    def get_one_goal(self, discord_user_id, media_type, amount, span):
        where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND amount={amount} AND span='{span}'"
        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        """
        
        return self.fetch(query)
    
    def delete_completed(self, discord_user_id, goal_type, amount, media_type, text):
        where_clause = f"""discord_user_id={discord_user_id} AND media_type='{str(media_type).upper()}' AND amount={amount} AND text='{text}' AND goal_type='{goal_type}'"""
        query = f"""
        DELETE FROM completed WHERE {where_clause}"""
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()

    def update_amount(self, goal, amount):
        where_clause = f"WHERE discord_user_id={goal.duid} AND goal_type='{goal.goal_type}' AND media_type='{goal.media_type.value}' AND amount={goal.amount} AND text='{goal.text}' AND span='{goal.span}' AND created_at='{goal.created_at}' AND end='{goal.end}'"
        query = f"""UPDATE goals SET current_amount={amount} {where_clause}"""
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()
        
    def update_end(self, goal, end):
        where_clause = f"WHERE discord_user_id={goal.duid} AND goal_type='{goal.goal_type}' AND media_type='{goal.media_type.value}' AND amount={goal.amount} AND text='{goal.text}' AND span='{goal.span}' AND created_at='{goal.created_at}' AND end='{goal.end}'"
        query = f"""UPDATE goals SET end='{end}' {where_clause}"""
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()
        
        
    def search_completed(self, goal):
        where_clause = f"WHERE discord_user_id = {goal.duid} and goal_type = '{goal.goal_type}' and media_type = '{goal.media_type.value}' and amount = {goal.amount} and text = '{goal.text}'"
        query = f"""DELETE FROM completed {where_clause}"""
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()