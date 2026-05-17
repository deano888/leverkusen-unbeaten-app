"""
commentary_loader.py
====================
Loads cached commentary from statsbomb_cache/commentary.csv
Used by app.py to display intro text and highlight commentary.
"""

import os
import pandas as pd

CACHE_DIR = "statsbomb_cache"

def _load() -> pd.DataFrame:
    path = f"{CACHE_DIR}/commentary.csv"
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def _find(df, home, away):
    if df.empty: return pd.DataFrame()
    return df[
        ((df["home_fd"]==home) & (df["away_fd"]==away)) |
        ((df["home_fd"]==away) & (df["away_fd"]==home))
    ]

def get_intro(home: str, away: str) -> str:
    """Return intro commentary text or empty string."""
    df = _load()
    m  = _find(df, home, away)
    intro = m[m["content_type"]=="intro"]
    if intro.empty: return ""
    return str(intro.iloc[0]["commentary"])

def get_highlight_commentary(home: str, away: str) -> list[str]:
    """
    Return list of commentary strings in highlight order.
    Index matches the combined shot+red_card sequence.
    """
    df = _load()
    m  = _find(df, home, away)
    hl = m[m["content_type"]=="highlight"].sort_values("highlight_idx")
    if hl.empty: return []
    return hl["commentary"].tolist()

def has_commentary(home: str, away: str) -> bool:
    """Return True if commentary exists for this match."""
    df = _load()
    return not _find(df, home, away).empty
