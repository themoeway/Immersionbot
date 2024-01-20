ACHIEVEMENTS = {
    "VN": [1, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 4_000_000, 10_000_000, float('inf')],
    "ANIME": [1, 12, 25, 100, 200, 500, 800, 1500, float('inf')],
    "READING": [1, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 4_000_000, 10_000_000, float('inf')],
    "BOOK": [1, 100, 250, 1000, 2500, 5000, 10_000, 20_000, float('inf')],
    "MANGA": [1, 250, 1250, 5000, 10_000, 25_000, 50_000, 100_000, float('inf')],
    "LISTENING": [1, 250, 500, 2000, 5000, 10_000, 25_000, 50_000, float('inf')],
    "READTIME": [1, 250, 500, 2000, 5000, 10_000, 25_000, 50_000, float('inf')],
}

PT_ACHIEVEMENTS = [1, 100, 300, 1000, 2000, 10_000, 25_000, 100_000, float('inf')]

ACHIEVEMENT_RANKS = ['Beginner', 'Initiate', 'Apprentice', 'Hobbyist', 'Enthusiast', 'Aficionado', 'Sage', 'Master']
ACHIEVEMENT_EMOJIS = [':new_moon:', ':new_moon_with_face:', ':waning_crescent_moon:', ':last_quarter_moon:', ':waning_gibbous_moon:', ':full_moon:', ':full_moon_with_face:', ':sun_with_face:']
ACHIEVEMENT_IDS = [1120790734476423270, 1120790825702527037, 1120790890038952066, 1120790964970213436, 1120791040463470702, 1120791104518901912, 1120791193366823112, 1120791256818266112]

EMOJI_TABLE = {
    # 'Yay': 658999234787278848,
    # 'NanaYes': 837211260155854849,
    # 'NanaYay': 837211306293067797,
    "990": 921933172432863283,
    "CatBlush": 933089264030339083,
    "CatTup": 948511239401799681,
    "ChikaTup": 918620369919828000,
    "ChubbyGero": 831348462305673286,
    "ChubbyGeroSwag": 929124878047641690,
    "CoolCat": 783741575582580758,
    "InuPero": 963127794194350110,
    "NadeshikoUma": 921677406849363989,
    "NanaJam": 882894763987177493,
    "NanaYay": 837211306293067797,
    "NanaYes": 877679734547427349,
    "NekoGero": 936524524231458897,
    "Peek": 918616198302793739,
    "ShimarinDango": 921677567084359702,
    "SugoiAA": 678245454068056097,
    "TachiSmile": 688824520362164303,
    "TohruFlex": 926637533994037328,
    "Yay": 658999234787278848,
    "Yousoroo": 698293340881289221,
    "Yousoroo2": 709339172602904586,
    "YuiPeace": 918623813552447529,
    "ajatt": 783749154807087134,
    "anki": 688802971089371185,
}

MULTIPLIERS = {
    'BOOK': 1,
    'MANGA': 0.2,
    'VN': 1 / 350,
    'ANIME': 9.5,
    'READING': 1 / 350,
    'LISTENING': 0.45,
    'READTIME': 0.45
}

_DB_NAME = 'prod.db'

TIMEFRAMES = ["WEEK, MONTH, YEAR, All"]

