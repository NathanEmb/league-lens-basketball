import os
from datetime import datetime

try:
    LEAGUE_ID = int(os.environ["LEAGUE_ID"])
except (ValueError, TypeError, KeyError):
    raise ValueError("Invalid environment variable values for LEAGUE_ID or YEAR. Ensure they exist and are integers.")

try:
    YEAR = int(os.environ.get("YEAR", datetime.now().year))
except (ValueError, TypeError):
    raise ValueError("Invalid environment variable value for YEAR. Ensure it is an integer.")

NINE_CATS = ["PTS", "BLK", "STL", "AST", "REB", "TO", "3PM", "FG%", "FT%"]
"""The 9 standard categories in fantasy basketball."""

ALL_RAW_DATA_TABLE_DEF = {
    "Team": str,
    "Standing": int,
    "PTS": int,
    "BLK": int,
    "STL": int,
    "AST": int,
    "REB": int,
    "TO": int,
    "FGM": int,
    "FGA": int,
    "FTM": int,
    "FTA": int,
    "3PM": int,
    "FG%": float,
    "FT%": float,
}

ALL_DATA_RANKED_TABLE_DEF = {
    "Team": str,
    "Standing": int,
    "Avg. Cat. Rank": int,
    "PTS": int,
    "BLK": int,
    "STL": int,
    "AST": int,
    "REB": int,
    "TO": int,
    "FGM": int,
    "FGA": int,
    "FTM": int,
    "FTA": int,
    "3PM": int,
    "FG%": int,
    "FT%": int,
}

CAT_ONLY_RAW_DATA_TABLE_DEF = {
    "Team": str,
    "Standing": int,
    "PTS": int,
    "BLK": int,
    "STL": int,
    "AST": int,
    "REB": int,
    "TO": int,
    "3PM": int,
    "FG%": float,
    "FT%": float,
}

CAT_ONLY_DATA_RANKED_TABLE_DEF = {
    "Team": str,
    "Standing": int,
    "Avg. Cat. Rank": int,
    "PTS": int,
    "BLK": int,
    "STL": int,
    "AST": int,
    "REB": int,
    "TO": int,
    "3PM": int,
    "FG%": int,
    "FT%": int,
}

WANT_BIG_NUM = ["PTS", "BLK", "STL", "AST", "REB", "FGM", "FGA", "FTM", "FTA", "3PM", "FG%", "FT%"]
"""All stats where a big number is better."""

WANT_BIG_NUM_CATS = ["PTS", "BLK", "STL", "AST", "REB", "3PM", "FG%", "FT%"]
"""Roto Categories where a big number is better."""

WANT_SMALL_NUM = ["Standing", "TO"]
"""All stats where a small number is better."""
