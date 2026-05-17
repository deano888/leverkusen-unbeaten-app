"""
recache_shots.py
================
Rebuilds ONLY shots.csv with the corrected running-score logic.
Much faster than re-running the full cache_statsbomb.py.

Usage:  py recache_shots.py
"""

import os, time
import pandas as pd
from statsbombpy import sb

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
def fd(n): return SB_TO_FD.get(n, n)

def outcome_str(val):
    if isinstance(val, dict): return val.get("name", "")
    return str(val) if val else ""

def tech_str(val):
    if isinstance(val, dict): return val.get("name", "")
    return str(val) if val else ""

def main():
    print("Rebuilding shots.csv with corrected running-score logic...\n")
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    matches["home_fd"] = matches["home_team"].map(lambda x: fd(x))
    matches["away_fd"] = matches["away_team"].map(lambda x: fd(x))

    shot_rows = []
    total = len(matches)

    for i, (_, m) in enumerate(matches.iterrows(), 1):
        mid     = m["match_id"]
        home_sb = m["home_team"]
        away_sb = m["away_team"]
        home_fd_ = m["home_fd"]
        away_fd_ = m["away_fd"]
        date    = str(m.get("match_date", ""))

        print(f"  [{i}/{total}] {home_fd_} vs {away_fd_}")

        try:
            events = sb.events(match_id=mid)
            shots  = events[events["type"] == "Shot"].copy()

            if shots.empty:
                print("    No shots found")
                continue

            # Sort by StatsBomb event index — true chronological order
            sort_col = "index" if "index" in shots.columns else "minute"
            shots = shots.sort_values(sort_col)

            h_score = 0
            a_score = 0

            for _, sh in shots.iterrows():
                out  = outcome_str(sh.get("shot_outcome", ""))
                is_goal = (out == "Goal")
                team_sb = str(sh.get("team", ""))
                team_fd_ = fd(team_sb)

                # Update running score BEFORE recording (score at moment of shot)
                # then update if it's a goal so score_after reflects post-goal state
                if is_goal:
                    if team_sb == home_sb: h_score += 1
                    else:                  a_score += 1

                loc   = sh.get("location") or [None, None]
                x_raw = float(loc[0]) if loc and len(loc) > 0 and loc[0] is not None else None
                y_raw = float(loc[1]) if loc and len(loc) > 1 and loc[1] is not None else None

                shot_rows.append({
                    "match_id":    mid,
                    "home_fd":     home_fd_,
                    "away_fd":     away_fd_,
                    "match_date":  date,
                    "team_fd":     team_fd_,
                    "player":      str(sh.get("player", "")),
                    "minute":      int(sh.get("minute", 0)),
                    "x":           x_raw,
                    "y":           y_raw,
                    "xg":          round(float(sh.get("shot_statsbomb_xg", 0) or 0), 4),
                    "is_goal":     int(is_goal),
                    "outcome":     out,
                    "technique":   tech_str(sh.get("shot_technique", "")),
                    "body_part":   tech_str(sh.get("shot_body_part", "")),
                    "score_after": f"{h_score}-{a_score}",
                    "home_score":  h_score,
                    "away_score":  a_score,
                })

            goals_in_match = sum(1 for r in shot_rows
                                 if r["home_fd"] == home_fd_ and r["away_fd"] == away_fd_
                                 and r["is_goal"] == 1)
            print(f"    {len([r for r in shot_rows if r['home_fd']==home_fd_ and r['away_fd']==away_fd_])} shots, "
                  f"{goals_in_match} goals, final score: {h_score}-{a_score}")

        except Exception as e:
            print(f"    ERROR: {e}")

        time.sleep(0.3)

    out_path = f"{CACHE_DIR}/shots.csv"
    pd.DataFrame(shot_rows).to_csv(out_path, index=False)
    print(f"\nDone! {len(shot_rows)} shot rows saved to {out_path}")
    print("Restart Streamlit to pick up the new data.")

if __name__ == "__main__":
    main()
