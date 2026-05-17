"""
recache_events.py
=================
Rebuilds ONLY events_key.csv with corrected red card detection.
StatsBomb stores red cards in TWO places:
  1. "Bad Behaviour" events (violent conduct, dissent)
  2. "Foul Committed" events with foul_committed_card = "Red Card" or "Second Yellow"

Run:  py recache_events.py

Takes ~2-3 minutes.
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
def fd(n): return SB_TO_FD.get(str(n), str(n))

def is_red(card_val):
    """Check if a card value (string or dict) is a red or second yellow."""
    if not card_val or str(card_val) in ("nan", "None", ""):
        return False
    s = str(card_val).lower()
    return "red" in s or "second yellow" in s

def get_card_name(val):
    if isinstance(val, dict):
        return val.get("name", "")
    return str(val) if val else ""

def main():
    print("Rebuilding events_key.csv with corrected red card detection...\n")

    matches_path = f"{CACHE_DIR}/matches.csv"
    if not os.path.exists(matches_path):
        print("ERROR: matches.csv not found. Run cache_statsbomb.py first.")
        return

    matches = pd.read_csv(matches_path)
    event_rows = []
    total = len(matches)

    for i, (_, m) in enumerate(matches.iterrows(), 1):
        mid      = m["match_id"]
        home_fd_ = m["home_fd"]
        away_fd_ = m["away_fd"]
        home_sb  = m["home_team"]
        away_sb  = m["away_team"]
        date     = str(m.get("match_date", ""))

        print(f"  [{i}/{total}] {home_fd_} vs {away_fd_}")

        try:
            events = sb.events(match_id=mid)

            # ── Goals (from shots) ─────────────────────────────────────────
            shots = events[events["type"] == "Shot"].copy()
            goal_shots = shots[shots["shot_outcome"].apply(
                lambda x: (x == "Goal") if isinstance(x, str)
                else (isinstance(x, dict) and x.get("name") == "Goal")
            )]
            goals_found = 0
            for _, g in goal_shots.iterrows():
                event_rows.append({
                    "match_id":   mid, "home_fd": home_fd_, "away_fd": away_fd_,
                    "match_date": date, "event_type": "goal",
                    "player":     str(g.get("player", "")),
                    "team_fd":    fd(g.get("team", "")),
                    "minute":     int(g.get("minute", 0)),
                    "xg":         round(float(g.get("shot_statsbomb_xg", 0) or 0), 3),
                })
                goals_found += 1

            # ── Red cards — method 1: Bad Behaviour events ─────────────────
            reds_found = 0
            bad = events[events["type"] == "Bad Behaviour"].copy()
            for _, r in bad.iterrows():
                card = r.get("bad_behaviour_card", "")
                card_name = get_card_name(card)
                if is_red(card_name) or is_red(card):
                    event_rows.append({
                        "match_id":   mid, "home_fd": home_fd_, "away_fd": away_fd_,
                        "match_date": date, "event_type": "red_card",
                        "player":     str(r.get("player", "")),
                        "team_fd":    fd(r.get("team", "")),
                        "minute":     int(r.get("minute", 0)),
                        "xg":         0.0,
                    })
                    reds_found += 1

            # ── Red cards — method 2: Foul Committed with red card ─────────
            fouls = events[events["type"] == "Foul Committed"].copy()
            for _, f in fouls.iterrows():
                # Check foul_committed_card column
                card = f.get("foul_committed_card", "")
                card_name = get_card_name(card)
                if is_red(card_name) or is_red(card):
                    event_rows.append({
                        "match_id":   mid, "home_fd": home_fd_, "away_fd": away_fd_,
                        "match_date": date, "event_type": "red_card",
                        "player":     str(f.get("player", "")),
                        "team_fd":    fd(f.get("team", "")),
                        "minute":     int(f.get("minute", 0)),
                        "xg":         0.0,
                    })
                    reds_found += 1

            print(f"    {goals_found} goals, {reds_found} red cards")

        except Exception as e:
            print(f"    ERROR: {e}")

        time.sleep(0.25)

    # Save
    df = pd.DataFrame(event_rows)
    out_path = f"{CACHE_DIR}/events_key.csv"
    df.to_csv(out_path, index=False)

    goals_total = len(df[df["event_type"] == "goal"])
    reds_total  = len(df[df["event_type"] == "red_card"])
    print(f"\nDone! {len(df)} rows saved to {out_path}")
    print(f"  Goals:     {goals_total}")
    print(f"  Red cards: {reds_total}")

    if reds_total > 0:
        print(f"\nRed cards found:")
        reds = df[df["event_type"] == "red_card"]
        print(reds[["home_fd","away_fd","player","team_fd","minute"]].to_string(index=False))

    print("\nRestart Streamlit to pick up the new data.")

if __name__ == "__main__":
    main()
