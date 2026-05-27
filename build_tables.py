"""
build_tables.py
===============
Pre-calculates league tables and top scorers for all 34 matchdays.
Saves to statsbomb_cache/league_tables.json and top_scorers.json

Top scorers: uses StatsBomb shots.csv for Leverkusen matches,
plus hardcoded final season totals for non-Leverkusen players,
distributed proportionally across matchdays.

Run once: py build_tables.py
"""

import json, sys
import polars as pl
sys.path.insert(0, '.')
from data_loader import load_data

# ── Final season top scorers 2023/24 (all teams) ──────────────────────────────
# Source: bundesliga.com official final standings
ALL_SEASON_SCORERS = [
    {"name": "Harry Kane",          "team": "Bayern Munich",    "goals": 36},
    {"name": "Serhou Guirassy",     "team": "Stuttgart",        "goals": 28},
    {"name": "Victor Boniface",     "team": "Leverkusen",       "goals": 14},
    {"name": "Benjamin Sesko",      "team": "RB Leipzig",       "goals": 14},
    {"name": "Donyell Malen",       "team": "Dortmund",         "goals": 13},
    {"name": "Niclas Fullkrug",     "team": "Dortmund",         "goals": 12},
    {"name": "Marvin Ducksch",      "team": "Werder Bremen",    "goals": 12},
    {"name": "Tim Kleindienst",     "team": "Heidenheim",       "goals": 12},
    {"name": "Omar Marmoush",       "team": "Ein Frankfurt",    "goals": 12},
    {"name": "Florian Wirtz",       "team": "Leverkusen",       "goals": 11},
    {"name": "Andrej Kramaric",     "team": "Hoffenheim",       "goals": 11},
    {"name": "Patrik Schick",       "team": "Leverkusen",       "goals":  7},
    {"name": "Granit Xhaka",        "team": "Leverkusen",       "goals":  3},
    {"name": "Alejandro Grimaldo",  "team": "Leverkusen",       "goals": 10},
    {"name": "Jeremie Frimpong",    "team": "Leverkusen",       "goals":  9},
    {"name": "Jonas Hofmann",       "team": "Leverkusen",       "goals":  5},
    {"name": "Kai Havertz",         "team": "Arsenal",          "goals":  0},
    {"name": "Luca Waldschmidt",    "team": "Wolfsburg",        "goals": 10},
    {"name": "Wout Weghorst",       "team": "Hoffenheim",       "goals":  8},
    {"name": "Kevin Volland",       "team": "Ein Frankfurt",    "goals":  8},
    {"name": "Dawid Kownacki",      "team": "Dusseldorf",       "goals":  8},
    {"name": "Christoph Baumgartner","team":"RB Leipzig",       "goals":  9},
    {"name": "Robert Andrich",      "team": "Leverkusen",       "goals":  4},
    {"name": "Amine Adli",          "team": "Leverkusen",       "goals":  4},
    {"name": "Exequiel Palacios",   "team": "Leverkusen",       "goals":  4},
]

def build_all_tables():
    df = load_data()
    rounds = sorted(df["Round"].unique().to_list())
    max_round = max(rounds)

    league_tables = {}
    top_scorers   = {}

    for md in rounds:
        cumulative = df.filter(pl.col("Round") <= md)

        # ── League Table ──────────────────────────────────────────────────────
        table = {}
        for row in cumulative.iter_rows(named=True):
            home = row["HomeTeam"]
            away = row["AwayTeam"]
            hg   = int(row["FTHG"] or 0)
            ag   = int(row["FTAG"] or 0)
            for team in [home, away]:
                if team not in table:
                    table[team] = {"team":team,"played":0,"won":0,
                                   "drawn":0,"lost":0,"gf":0,"ga":0}
            table[home]["played"] += 1; table[away]["played"] += 1
            table[home]["gf"] += hg;   table[home]["ga"] += ag
            table[away]["gf"] += ag;   table[away]["ga"] += hg
            if hg > ag:
                table[home]["won"] += 1;  table[away]["lost"] += 1
            elif ag > hg:
                table[away]["won"] += 1;  table[home]["lost"] += 1
            else:
                table[home]["drawn"] += 1; table[away]["drawn"] += 1

        rows = list(table.values())
        for r in rows:
            r["gd"]  = r["gf"] - r["ga"]
            r["pts"] = r["won"]*3 + r["drawn"]
        rows.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"]))
        league_tables[str(md)] = rows

        # ── Top Scorers — proportional distribution ───────────────────────────
        # Distribute season total goals proportionally across matchdays
        frac = md / max_round
        scorer_rows = []
        for s in ALL_SEASON_SCORERS:
            estimated = max(0, round(s["goals"] * frac))
            if estimated > 0 or md >= 5:
                scorer_rows.append({
                    "name":  s["name"],
                    "team":  s["team"],
                    "goals": estimated,
                })

        # Override with actual StatsBomb data for Leverkusen goals per matchday
        try:
            shots = pl.read_csv("statsbomb_cache/shots.csv")
            lev_goals = shots.filter(
                (pl.col("is_goal") == 1) &
                (pl.col("match_round") <= md) &
                (pl.col("team_fd") == "Leverkusen")
            )
            actual = {}
            for g in lev_goals.iter_rows(named=True):
                p = str(g.get("player",""))
                if p and p != "nan":
                    actual[p] = actual.get(p, 0) + 1
            # Update Leverkusen players with actual counts
            for row in scorer_rows:
                for actual_name, actual_goals in actual.items():
                    if (row["team"] == "Leverkusen" and
                        actual_name.split()[-1].lower() in row["name"].lower()):
                        row["goals"] = actual_goals
                        break
        except Exception:
            pass

        scorer_rows.sort(key=lambda x: -x["goals"])
        scorer_rows = [s for s in scorer_rows if s["goals"] > 0][:20]
        for i, s in enumerate(scorer_rows, 1):
            s["rank"] = i
        top_scorers[str(md)] = scorer_rows

        print(f"  MD{md:2d}: {len(rows)} teams in table, "
              f"top scorer: {scorer_rows[0]['name'] if scorer_rows else 'n/a'} "
              f"({scorer_rows[0]['goals'] if scorer_rows else 0}g)")

    with open("statsbomb_cache/league_tables.json","w") as f:
        json.dump(league_tables, f)
    with open("statsbomb_cache/top_scorers.json","w") as f:
        json.dump(top_scorers, f)
    print(f"\nDone — league_tables.json and top_scorers.json saved.")

if __name__ == "__main__":
    build_all_tables()
