"""
shot_loader.py
==============
Load shot data from statsbomb_cache/shots.csv and prepare
shot map sequences for the rotating popup display.

Shot selection logic:
  - 0 goals  → top 3 shots by xG
  - 1-2 goals → all goals + top 2 non-goal shots by xG
  - 3+ goals  → goals only

Each shot dict ready for rendering:
  player, team_fd, minute, x, y, xg, is_goal, outcome,
  technique, body_part, score_after, home_fd, away_fd
"""

import os
import pandas as pd

CACHE_DIR = "statsbomb_cache"


def _f(p): return f"{CACHE_DIR}/{p}"
def _exists(p): return os.path.exists(_f(p))


def _find_shots(home: str, away: str) -> pd.DataFrame:
    """Return all shots for this match regardless of home/away order in cache.
    Uses match_id to avoid returning duplicate rows from bidirectional cache storage."""
    if not _exists("shots.csv"):
        return pd.DataFrame()
    try:
        df = pd.read_csv(_f("shots.csv"))
    except Exception:
        return pd.DataFrame()
    if df.empty or len(df.columns) == 0:
        return pd.DataFrame()

    # Find all matching rows (either direction)
    match = df[
        ((df["home_fd"] == home) & (df["away_fd"] == away)) |
        ((df["home_fd"] == away) & (df["away_fd"] == home))
    ].copy()

    if match.empty:
        return match

    # If multiple match_ids found (bidirectional cache), keep only the first one
    # This prevents score counters being duplicated/reset
    if "match_id" in match.columns and match["match_id"].nunique() > 1:
        first_id = match["match_id"].iloc[0]
        match = match[match["match_id"] == first_id].copy()

    return match


def get_shot_sequence(home: str, away: str) -> list[dict]:
    """
    Return an ordered list of shot dicts to display as rotating maps.
    Selection logic based on total goals scored.
    Always sorted by minute ascending.
    """
    shots = _find_shots(home, away)
    if shots.empty:
        return []

    # Ensure types
    shots["xg"]      = pd.to_numeric(shots["xg"], errors="coerce").fillna(0)
    shots["is_goal"]  = shots["is_goal"].fillna(0).astype(int)
    shots["minute"]   = pd.to_numeric(shots["minute"], errors="coerce").fillna(0).astype(int)

    # Deduplicate on stable shot identity fields
    dedup_cols = [c for c in ["match_id", "player", "minute", "is_goal"] if c in shots.columns]
    shots = shots.drop_duplicates(subset=dedup_cols)

    goals     = shots[shots["is_goal"] == 1].sort_values("minute")
    non_goals = shots[shots["is_goal"] == 0].sort_values("xg", ascending=False)
    n_goals   = len(goals)

    if n_goals == 0:
        selected = shots.sort_values("xg", ascending=False).head(3)
    elif n_goals <= 2:
        top_non_goals = non_goals.head(2)
        selected = pd.concat([goals, top_non_goals])
    else:
        selected = goals  # 3+ goals: goals only

    # Always return in chronological order
    selected = selected.sort_values("minute")

    return [_row_to_dict(r) for _, r in selected.iterrows()]


def _row_to_dict(r) -> dict:
    return {
        "player":      str(r.get("player", "Unknown")),
        "team_fd":     str(r.get("team_fd", "")),
        "home_fd":     str(r.get("home_fd", "")),
        "away_fd":     str(r.get("away_fd", "")),
        "minute":      int(r.get("minute", 0)),
        "x":           float(r["x"]) if pd.notna(r.get("x")) else 60.0,
        "y":           float(r["y"]) if pd.notna(r.get("y")) else 40.0,
        "xg":          round(float(r.get("xg", 0)), 3),
        "is_goal":     int(r.get("is_goal", 0)),
        "outcome":     str(r.get("outcome", "")),
        "technique":   str(r.get("technique", "")),
        "body_part":   str(r.get("body_part", "")),
        "score_after": str(r.get("score_after", "0-0")),
        "home_score":  int(r.get("home_score", 0)),
        "away_score":  int(r.get("away_score", 0)),
        "match_date":  str(r.get("match_date", "")),
    }


def get_all_shots_for_commentary(home: str, away: str) -> list[dict]:
    """
    Return ALL shots for this match — used for AI commentary generation.
    Includes every field needed: player, team, x, y, xg, is_goal, outcome,
    score_after, minute, technique, body_part.
    """
    shots = _find_shots(home, away)
    if shots.empty:
        return []
    shots = shots.sort_values("minute")
    return [_row_to_dict(r) for _, r in shots.iterrows()]
