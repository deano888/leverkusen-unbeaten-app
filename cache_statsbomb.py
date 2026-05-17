"""
cache_statsbomb.py
==================
Run ONCE to download all StatsBomb 2023/24 Bundesliga data and cache as CSVs.
After running, the app loads instantly from disk.

Usage:  py cache_statsbomb.py

Output in ./statsbomb_cache/:
    matches.csv       - match metadata
    xg_by_match.csv   - home/away xG per match
    players.csv       - players with minutes played + xG per match
    events_key.csv    - goals and red cards
"""

import os, time
import pandas as pd
from statsbombpy import sb

CACHE_DIR = "statsbomb_cache"
COMPETITION_ID = 9
SEASON_ID = 281   # 2023/24

SB_TO_FD = {
    "Bayer Leverkusen":          "Leverkusen",
    "1. FC Heidenheim 1846":     "Heidenheim",
    "SV Darmstadt 98":           "Darmstadt",
    "1. FSV Mainz 05":           "Mainz",
    "Borussia Dortmund":         "Dortmund",
    "RB Leipzig":                "RB Leipzig",
    "VfB Stuttgart":             "Stuttgart",
    "SC Freiburg":               "Freiburg",
    "FC Bayern München":         "Bayern Munich",
    "Eintracht Frankfurt":       "Ein Frankfurt",
    "VfL Wolfsburg":             "Wolfsburg",
    "1. FC Köln":                "FC Koln",
    "TSG Hoffenheim":            "Hoffenheim",
    "Werder Bremen":             "Werder Bremen",
    "VfL Bochum 1848":           "Bochum",
    "FC Augsburg":               "Augsburg",
    "Borussia Mönchengladbach":  "M'gladbach",
    "1. FC Union Berlin":        "Union Berlin",
}
def fd(n): return SB_TO_FD.get(n, n)

def calc_minutes(events_df, player_name, team_name):
    """Calculate minutes played — respects substitutions AND red cards."""
    # Player came ON as sub
    if "substitution_replacement" in events_df.columns:
        subbed_on = events_df[
            (events_df["type"] == "Substitution") &
            (events_df["team"] == team_name) &
            (events_df["substitution_replacement"] == player_name)
        ]
    else:
        subbed_on = pd.DataFrame()

    # Player was substituted OFF
    subbed_off = events_df[
        (events_df["type"] == "Substitution") &
        (events_df["team"] == team_name) &
        (events_df["player"] == player_name)
    ]

    # Player received a red card (sent off)
    red_events = events_df[
        (events_df["player"] == player_name) &
        (events_df["type"].isin(["Bad Behaviour", "Foul Committed"]))
    ]
    red_minute = None
    for _, r in red_events.iterrows():
        card = r.get("bad_behaviour_card", "") or r.get("foul_committed_card", "")
        card_str = card.get("name","") if isinstance(card, dict) else str(card or "")
        if "Red" in card_str or "Second Yellow" in card_str:
            red_minute = int(r["minute"])
            break

    start_min = 0
    end_min = None

    if not subbed_on.empty:
        start_min = int(subbed_on.iloc[0]["minute"])

    if not subbed_off.empty:
        end_min = int(subbed_off.iloc[0]["minute"])

    # Red card caps minutes — player left the pitch at that minute
    if red_minute is not None:
        end_min = red_minute if end_min is None else min(end_min, red_minute)

    if end_min is None:
        last_event = events_df[events_df["period"] <= 2].tail(1)
        end_min = max(int(last_event.iloc[0]["minute"]), 90) if not last_event.empty else 90

    return max(end_min - start_min, 0)

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"Saving to ./{CACHE_DIR}/\n")

    print("Fetching match list...")
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    matches["home_fd"] = matches["home_team"].map(fd)
    matches["away_fd"] = matches["away_team"].map(fd)
    matches.to_csv(f"{CACHE_DIR}/matches.csv", index=False)
    print(f"  {len(matches)} matches saved\n")

    xg_rows, player_rows, event_rows, shot_rows = [], [], [], []
    total = len(matches)

    for i, (_, match) in enumerate(matches.iterrows(), 1):
        match_id   = match["match_id"]
        home_sb    = match["home_team"]
        away_sb    = match["away_team"]
        home_fd_   = match["home_fd"]
        away_fd_   = match["away_fd"]
        match_date = str(match.get("match_date", ""))
        print(f"  [{i}/{total}] {home_fd_} vs {away_fd_}")

        try:
            events = sb.events(match_id=match_id)

            # ── xG ──────────────────────────────────────────────────────────
            shots = events[events["type"] == "Shot"].copy()
            home_xg = shots[shots["team"] == home_sb]["shot_statsbomb_xg"].sum()
            away_xg = shots[shots["team"] == away_sb]["shot_statsbomb_xg"].sum()
            xg_rows.append({
                "match_id": match_id, "home_fd": home_fd_, "away_fd": away_fd_,
                "match_date": match_date,
                "home_xg": round(float(home_xg), 3),
                "away_xg": round(float(away_xg), 3),
            })

            # ── Player xG + minutes ──────────────────────────────────────────
            player_xg = (
                shots.groupby(["player", "team"])["shot_statsbomb_xg"]
                .sum().reset_index()
                .rename(columns={"shot_statsbomb_xg": "xg"})
            )
            player_goals = (
                shots[shots["shot_outcome"].apply(
                    lambda x: x == "Goal" if isinstance(x,str)
                    else (isinstance(x,dict) and x.get("name")=="Goal")
                )].groupby("player").size().reset_index(name="goals")
            )

            # Get all players who appeared in events
            all_players = events[events["player"].notna()][["player","team"]].drop_duplicates()

            for _, prow in all_players.iterrows():
                pname    = prow["player"]
                team_sb  = prow["team"]
                team_fd_ = fd(team_sb)
                mins     = calc_minutes(events, pname, team_sb)
                if mins == 0:
                    continue
                xg_val = float(player_xg[player_xg["player"] == pname]["xg"].sum())
                goals_val = int(player_goals[player_goals["player"] == pname]["goals"].sum()) if not player_goals[player_goals["player"] == pname].empty else 0
                # Get position from lineups if available
                pos_val = ""
                try:
                    lups = sb.lineups(match_id=match_id)
                    for tsb, ldf in lups.items():
                        if fd(tsb) == team_fd_:
                            row_p = ldf[ldf["player_name"] == pname]
                            if not row_p.empty and row_p.iloc[0].get("positions"):
                                pos_val = row_p.iloc[0]["positions"][0].get("position","")
                except Exception:
                    pass
                player_rows.append({
                    "match_id":    match_id,
                    "home_fd":     home_fd_,
                    "away_fd":     away_fd_,
                    "match_date":  match_date,
                    "team_fd":     team_fd_,
                    "player_name": pname,
                    "minutes":     mins,
                    "xg":          round(xg_val, 2),
                    "goals":       goals_val,
                    "position":    pos_val,
                })

            # ── Goals ────────────────────────────────────────────────────────
            goal_events = shots[shots["shot_outcome"].apply(
                lambda x: x == "Goal" if isinstance(x,str)
                else (isinstance(x,dict) and x.get("name")=="Goal")
            )]
            for _, g in goal_events.iterrows():
                event_rows.append({
                    "match_id": match_id, "home_fd": home_fd_, "away_fd": away_fd_,
                    "match_date": match_date, "event_type": "goal",
                    "player": str(g.get("player","")), "team_fd": fd(str(g.get("team",""))),
                    "minute": int(g.get("minute",0)), "xg": round(float(g.get("shot_statsbomb_xg",0) or 0),3),
                })

            # ── All shots (for shot maps + commentary) ────────────────────
            # Sort by StatsBomb index (true chronological event order within match)
            sort_col = "index" if "index" in shots.columns else "minute"
            h_score, a_score = 0, 0
            for _, sh in shots.sort_values(sort_col).iterrows():
                try:
                    outcome_raw = sh.get("shot_outcome", "")
                    if isinstance(outcome_raw, dict):
                        outcome_str = outcome_raw.get("name", "")
                    else:
                        outcome_str = str(outcome_raw)
                    is_goal = (outcome_str == "Goal")
                    sh_team_sb = str(sh.get("team", ""))
                    sh_team_fd = fd(sh_team_sb)
                    if is_goal:
                        # Compare against StatsBomb home/away team names (not fd names)
                        if sh_team_sb == home_sb: h_score += 1
                        else: a_score += 1
                    loc = sh.get("location") or [None, None]
                    x_raw = float(loc[0]) if loc and len(loc) > 0 and loc[0] is not None else None
                    y_raw = float(loc[1]) if loc and len(loc) > 1 and loc[1] is not None else None
                    tech_raw = sh.get("shot_technique", "")
                    tech_str = tech_raw.get("name","") if isinstance(tech_raw, dict) else str(tech_raw or "")
                    bp_raw = sh.get("shot_body_part", "")
                    bp_str = bp_raw.get("name","") if isinstance(bp_raw, dict) else str(bp_raw or "")
                    shot_rows.append({
                        "match_id":   match_id,
                        "home_fd":    home_fd_,
                        "away_fd":    away_fd_,
                        "match_date": match_date,
                        "team_fd":    sh_team_fd,
                        "player":     str(sh.get("player", "")),
                        "minute":     int(sh.get("minute", 0)),
                        "x":          x_raw,
                        "y":          y_raw,
                        "xg":         round(float(sh.get("shot_statsbomb_xg", 0) or 0), 4),
                        "is_goal":    int(is_goal),
                        "outcome":    outcome_str,
                        "technique":  tech_str,
                        "body_part":  bp_str,
                        "score_after": f"{h_score}-{a_score}",
                        "home_score": h_score,
                        "away_score": a_score,
                    })
                except Exception as se:
                    print(f"      Shot row error: {se}")

            # ── Red cards ────────────────────────────────────────────────────
            cards = events[events["type"] == "Bad Behaviour"]
            reds  = cards[cards["bad_behaviour_card"].apply(
                lambda x: ("Red" in str(x)) if x else False
            )]
            for _, r in reds.iterrows():
                event_rows.append({
                    "match_id": match_id, "home_fd": home_fd_, "away_fd": away_fd_,
                    "match_date": match_date, "event_type": "red_card",
                    "player": str(r.get("player","")), "team_fd": fd(str(r.get("team",""))),
                    "minute": int(r.get("minute",0)), "xg": 0.0,
                })

        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(0.3)

    pd.DataFrame(xg_rows).to_csv(f"{CACHE_DIR}/xg_by_match.csv", index=False)
    pd.DataFrame(player_rows).to_csv(f"{CACHE_DIR}/players.csv", index=False)
    pd.DataFrame(event_rows).to_csv(f"{CACHE_DIR}/events_key.csv", index=False)
    pd.DataFrame(shot_rows).to_csv(f"{CACHE_DIR}/shots.csv", index=False)

    print(f"\nDone! Files saved to ./{CACHE_DIR}/")
    print(f"  xg_by_match.csv : {len(xg_rows)} rows")
    print(f"  players.csv     : {len(player_rows)} rows")
    print(f"  events_key.csv  : {len(event_rows)} rows")
    print(f"  shots.csv       : {len(shot_rows)} rows")

if __name__ == "__main__":
    main()
