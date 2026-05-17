"""
xg_loader.py  -  StatsBomb data loader (cache-first)
Run cache_statsbomb.py once first to build the cache.
"""
import os
import pandas as pd

CACHE_DIR = "statsbomb_cache"
COMPETITION_ID = 9
SEASON_ID = 281

SB_TO_FD = {
    "Bayer Leverkusen":"Leverkusen","1. FC Heidenheim 1846":"Heidenheim",
    "SV Darmstadt 98":"Darmstadt","1. FSV Mainz 05":"Mainz",
    "Borussia Dortmund":"Dortmund","RB Leipzig":"RB Leipzig",
    "VfB Stuttgart":"Stuttgart","SC Freiburg":"Freiburg",
    "FC Bayern München":"Bayern Munich","Eintracht Frankfurt":"Ein Frankfurt",
    "VfL Wolfsburg":"Wolfsburg","1. FC Köln":"FC Koln",
    "TSG Hoffenheim":"Hoffenheim","Werder Bremen":"Werder Bremen",
    "VfL Bochum 1848":"Bochum","FC Augsburg":"Augsburg",
    "Borussia Mönchengladbach":"M'gladbach","1. FC Union Berlin":"Union Berlin",
}

def _f(p): return f"{CACHE_DIR}/{p}"
def _exists(p): return os.path.exists(_f(p))


def build_xg_lookup() -> dict:
    """
    Return {(team_a, team_b): (team_a_xg, team_b_xg)} for every ordering.
    Bidirectional so lookup works regardless of home/away order in football-data CSV.
    """
    if _exists("xg_by_match.csv"):
        df = pd.read_csv(_f("xg_by_match.csv"))
        lookup = {}
        for _, r in df.iterrows():
            h, a = r["home_fd"], r["away_fd"]
            hxg, axg = r["home_xg"], r["away_xg"]
            # Store both orderings — values are always (first_team_xg, second_team_xg)
            lookup[(h, a)] = (hxg, axg)
            lookup[(a, h)] = (axg, hxg)
        return lookup
    try:
        from statsbombpy import sb
        matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
        lookup = {}
        for _, m in matches.iterrows():
            hfd = SB_TO_FD.get(m["home_team"], m["home_team"])
            afd = SB_TO_FD.get(m["away_team"], m["away_team"])
            events = sb.events(match_id=m["match_id"])
            shots = events[events["type"] == "Shot"]
            hxg = round(float(shots[shots["team"] == m["home_team"]]["shot_statsbomb_xg"].sum()), 2)
            axg = round(float(shots[shots["team"] == m["away_team"]]["shot_statsbomb_xg"].sum()), 2)
            lookup[(hfd, afd)] = (hxg, axg)
            lookup[(afd, hfd)] = (axg, hxg)
        return lookup
    except Exception as e:
        print(f"xG API fallback failed: {e}")
        return {}


def get_match_xg(lookup: dict, home: str, away: str):
    """Try both orderings — returns (home_xg, away_xg) or (None, None)."""
    result = lookup.get((home, away))
    if result is None:
        result = lookup.get((away, home))
        if result is not None:
            result = (result[1], result[0])  # flip so home is first
    return (None, None) if result is None else result


def _find_match_rows(df: pd.DataFrame, home: str, away: str) -> pd.DataFrame:
    """
    Return rows for this match regardless of which way home/away were stored.
    Deduplicates by match_id so bidirectional cache doesn't double-return rows.
    """
    # Try exact match first
    exact = df[(df["home_fd"] == home) & (df["away_fd"] == away)]
    if not exact.empty:
        return exact
    # Try reversed
    reversed_ = df[(df["home_fd"] == away) & (df["away_fd"] == home)]
    return reversed_


def get_players(home: str, away: str) -> dict:
    """
    Return {team_fd: [{"name":..., "minutes":..., "xg":..., "goals":..., "position":...}]}
    Only players with minutes > 0. No duplicates.
    """
    if not _exists("players.csv"):
        return {}
    df = pd.read_csv(_f("players.csv"))
    match = _find_match_rows(df, home, away)
    match = match[match["minutes"] > 0]
    if match.empty:
        return {}

    result = {}
    for team in [home, away]:
        tdf = match[match["team_fd"] == team].copy()
        # Deduplicate by player_name keeping highest minutes (safety net)
        tdf = tdf.sort_values("minutes", ascending=False).drop_duplicates("player_name")
        result[team] = [
            {
                "name":     r["player_name"],
                "minutes":  int(r["minutes"]),
                "xg":       round(float(r["xg"]), 2),
                "goals":    int(r["goals"]),
                "position": str(r["position"]) if "position" in r and str(r["position"]) != "nan" else "",
            }
            for _, r in tdf.iterrows()
        ]
    return result


def get_key_events(home: str, away: str) -> dict:
    if not _exists("events_key.csv"):
        return {"goals": [], "red_cards": []}
    df = pd.read_csv(_f("events_key.csv"))
    match = _find_match_rows(df, home, away)
    goals = match[match["event_type"] == "goal"].sort_values("minute")
    reds  = match[match["event_type"] == "red_card"].sort_values("minute")
    return {
        "goals": [
            {"player": r["player"], "team_fd": r["team_fd"],
             "minute": int(r["minute"]), "xg": round(float(r["xg"]), 2)}
            for _, r in goals.iterrows()
        ],
        "red_cards": [
            {"player": r["player"], "team_fd": r["team_fd"], "minute": int(r["minute"])}
            for _, r in reds.iterrows()
        ],
    }
