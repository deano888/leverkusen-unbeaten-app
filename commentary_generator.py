"""
commentary_generator.py
========================
Generates match intro + per-highlight commentary using the Claude API.
Run ONCE per season — saves to statsbomb_cache/commentary.csv.

Shows the insight brief for your review before calling the API.

Usage:
    py commentary_generator.py                  # generate all missing matches
    py commentary_generator.py --match Augsburg  # generate one specific match
    py commentary_generator.py --preview         # show briefs only, no API calls
"""

import os, sys, json, time, argparse, re
try:
    from player_nationalities import get_goal_cry, LEVERKUSEN_PHRASES
except ImportError:
    def get_goal_cry(name): return "GOAAAAAL!", "English", "🌍"
    LEVERKUSEN_PHRASES = {}

try:
    from context_enricher import enrich_shot_context, build_context_flags, get_match_id_for_teams
except ImportError:
    def enrich_shot_context(*a, **k): return None
    def build_context_flags(ctx): return ""
    def get_match_id_for_teams(*a): return None
import pandas as pd
import requests

CACHE_DIR    = "statsbomb_cache"
OUT_CSV      = f"{CACHE_DIR}/commentary.csv"
API_URL      = "https://api.anthropic.com/v1/messages"
MODEL        = "claude-haiku-4-5-20251001"   # fast + cheap

# ── Leverkusen season player stats (from Understat 2023/24) ─────────────────
PLAYER_SEASON = {
    "Victor Okoh Boniface":          {"g":14, "a":8,  "apps":23, "xg":16.99, "note":"top scorer"},
    "Florian Wirtz":                 {"g":11, "a":11, "apps":32, "xg":9.36,  "note":"creative engine"},
    "Alejandro Grimaldo Garcia":     {"g":10, "a":13, "apps":33, "xg":5.48,  "note":"attacking fullback"},
    "Alex Grimaldo":                 {"g":10, "a":13, "apps":33, "xg":5.48,  "note":"attacking fullback"},
    "Jeremie Frimpong":              {"g":9,  "a":7,  "apps":31, "xg":10.86, "note":"marauding fullback"},
    "Patrik Schick":                 {"g":7,  "a":0,  "apps":20, "xg":6.78,  "note":"clinical striker"},
    "Jonas Hofmann":                 {"g":5,  "a":7,  "apps":32, "xg":6.53,  "note":"consistent winger"},
    "Nathan Tella":                  {"g":5,  "a":2,  "apps":24, "xg":3.71,  "note":"impact sub"},
    "Jonathan Tah":                  {"g":4,  "a":1,  "apps":31, "xg":2.29,  "note":"commanding centre-back"},
    "Robert Andrich":                {"g":4,  "a":2,  "apps":28, "xg":2.21,  "note":"driving midfielder"},
    "Amine Adli":                    {"g":4,  "a":6,  "apps":23, "xg":3.68,  "note":"creative wide player"},
    "Exequiel Alejandro Palacios":   {"g":4,  "a":4,  "apps":24, "xg":3.47,  "note":"box-to-box midfielder"},
    "Granit Xhaka":                  {"g":3,  "a":0,  "apps":33, "xg":1.41,  "note":"midfield metronome"},
    "Josip Stanisic":                {"g":3,  "a":1,  "apps":20, "xg":0.70,  "note":"versatile fullback"},
    "Adam Hlozek":                   {"g":2,  "a":3,  "apps":23, "xg":3.05,  "note":"energetic forward"},
    "Odilon Kossonou":               {"g":1,  "a":0,  "apps":22, "xg":0.67,  "note":"powerful defender"},
    "Piero Martin Hincapie Reyna":   {"g":1,  "a":2,  "apps":26, "xg":2.35,  "note":"composed defender"},
    "Victor Boniface":               {"g":14, "a":8,  "apps":23, "xg":16.99, "note":"top scorer"},
    "Florian Wirtz ⚽":              {"g":11, "a":11, "apps":32, "xg":9.36,  "note":"creative engine"},
}

def fd_to_sb(name):
    """Fuzzy match player name to season stats."""
    if name in PLAYER_SEASON: return PLAYER_SEASON[name]
    for k, v in PLAYER_SEASON.items():
        # Match on last name
        last = name.split()[-1].lower()
        if last in k.lower(): return v
    return None


# ── Insight brief builder ─────────────────────────────────────────────────────

def build_match_brief(home, away, shots_df, events_df, xg_df, match_round):
    """
    Returns a structured dict of match-level insights for the intro commentary.
    """
    is_lev_home = (home == "Leverkusen")
    lev_goals   = int(shots_df[(shots_df["team_fd"]=="Leverkusen") & (shots_df["is_goal"]==1)]["is_goal"].sum())
    opp_goals   = int(shots_df[(shots_df["team_fd"]!=  "Leverkusen") & (shots_df["is_goal"]==1)]["is_goal"].sum())
    total_goals = lev_goals + opp_goals

    # Match xG
    xg_row = xg_df[
        ((xg_df["home_fd"]==home) & (xg_df["away_fd"]==away)) |
        ((xg_df["home_fd"]==away) & (xg_df["away_fd"]==home))
    ]
    lev_xg = opp_xg = None
    if not xg_row.empty:
        r = xg_row.iloc[0]
        if r["home_fd"] == "Leverkusen":
            lev_xg, opp_xg = r["home_xg"], r["away_xg"]
        else:
            lev_xg, opp_xg = r["away_xg"], r["home_xg"]

    # Goal diff
    goal_diff = lev_goals - opp_goals

    # Red cards
    reds = events_df[events_df["event_type"]=="red_card"]

    # Goals by minute for drama flags
    goal_events = shots_df[shots_df["is_goal"]==1].sort_values("minute")

    # Player goal counts this match
    lev_goal_events = goal_events[goal_events["team_fd"]=="Leverkusen"]
    player_goals_match = lev_goal_events.groupby("player").size().to_dict()
    scorers = lev_goal_events["player"].tolist()

    # Season context for scorers
    scorer_context = {}
    for p in set(scorers):
        ps = fd_to_sb(p)
        if ps:
            scorer_context[p] = ps

    # Flags
    flags = {
        # Result flags
        "lev_won":      goal_diff > 0,
        "lev_drew":     goal_diff == 0,
        "lev_lost":     goal_diff < 0,
        "easy_win":     goal_diff >= 4,
        "ran_riot":     goal_diff >= 5,
        "tight_game":   total_goals <= 3 and abs(goal_diff) == 1,
        "action_packed": total_goals >= 5 and abs(goal_diff) == 1,
        "ent_draw":     goal_diff == 0 and total_goals >= 4,

        # Specific narrative
        "unbeaten_run":  match_round == 34,
        "title_clincher": match_round == 29,
        "few_chances":   lev_xg is not None and lev_xg < 0.3,
        "dominant_xg":   lev_xg is not None and opp_xg is not None and lev_xg > opp_xg * 2,

        # Match events
        "has_red_card":  len(reds) > 0,
        "red_card_team": reds.iloc[0]["team_fd"] if len(reds) > 0 else None,
        "red_minute":    int(reds.iloc[0]["minute"]) if len(reds) > 0 else None,
        "late_drama":    any(int(m) > 85 for m in goal_events["minute"]),
        "early_goal":    any(int(m) < 15 for m in goal_events["minute"]),

        # Player storylines
        "brace_scorer":  [p for p, g in player_goals_match.items() if g >= 2],
        "hattrick":      [p for p, g in player_goals_match.items() if g >= 3],
        "scorer_context": scorer_context,
        "lev_scorers":   list(set(scorers)),

        # Stats
        "lev_goals":    lev_goals,
        "opp_goals":    opp_goals,
        "lev_xg":       round(lev_xg, 2) if lev_xg else None,
        "opp_xg":       round(opp_xg, 2) if opp_xg else None,
        "home":         home,
        "away":         away,
        "opponent":     away if home=="Leverkusen" else home,
        "lev_home":     is_lev_home,
        "round":        match_round,
    }
    return flags


def build_highlight_brief(shot, match_brief, player_goal_num=1):
    """
    Returns a dict of insight flags for a single highlight (shot or red card).
    """
    if shot.get("type") == "red_card":
        return {
            "type":       "red_card",
            "player":     shot["player"],
            "team":       shot["team_fd"],
            "minute":     shot["minute"],
            "score_at":   shot.get("score_at","—"),
            "early_red":  shot["minute"] < 40,
            "is_opponent_red": shot["team_fd"] != "Leverkusen",
        }

    is_goal    = shot["is_goal"] == 1
    xg         = shot["xg"]
    minute     = shot["minute"]
    player     = shot["player"]
    score      = shot.get("score_after","")
    ps         = fd_to_sb(player)

    # Score context
    parts      = score.split("-") if "-" in score else ["0","0"]
    h_score, a_score = int(parts[0]), int(parts[1])
    lev_score  = h_score if shot["home_fd"]=="Leverkusen" else a_score
    opp_score  = a_score if shot["home_fd"]=="Leverkusen" else h_score

    is_lev_goal = is_goal and shot["team_fd"] == "Leverkusen"
    is_opp_goal = is_goal and shot["team_fd"] != "Leverkusen"

    return {
        "type":         "shot",
        "is_goal":      is_goal,
        "is_lev_goal":  is_lev_goal,
        "is_opp_goal":  is_opp_goal,
        "player":       player,
        "team":         shot["team_fd"],
        "minute":       minute,
        "xg":           xg,
        "score_after":  score,
        "outcome":      shot.get("outcome",""),

        # Flags — always from Leverkusen's perspective
        "is_opener":       is_lev_goal and lev_score==1 and opp_score==0 and minute < 15,
        "is_equaliser":    is_lev_goal and lev_score == opp_score,
        "is_go_ahead":     is_lev_goal and lev_score == opp_score + 1,
        "is_consolation":  is_opp_goal and opp_score < lev_score,
        "opp_equaliser":   is_opp_goal and opp_score == lev_score,
        "opp_takes_lead":  is_opp_goal and opp_score > lev_score,
        "is_winner":       is_lev_goal and score == f"{match_brief['lev_goals']}-{match_brief['opp_goals']}",
        "is_low_xg_goal":  is_goal and xg < 0.08,
        "is_high_xg_goal": is_goal and xg > 0.50,
        "is_screamer":     is_goal and xg < 0.05,
        "late_drama":      minute > 85,
        # Scoring milestone — only flag what THIS goal represents
        # brace: player scored exactly 2 in match AND this is goal 2
        # hattrick_complete: player scored 3+ AND this is goal 3 exactly
        # suppress brace flag if player goes on to score hat-trick
        "brace":             (player in match_brief.get("brace_scorer",[]) and
                              player not in match_brief.get("hattrick",[]) and
                              player_goal_num == 2),
        "hattrick_complete": (player in match_brief.get("hattrick",[]) and
                              player_goal_num == 3),
        "hattrick_extend":   (player in match_brief.get("hattrick",[]) and
                              player_goal_num > 3),

        # Shot position (for distance assessment)
        "x":              shot.get("x", 90),
        "y":              shot.get("y", 40),

        # Player season context
        "season_goals":    ps["g"]    if ps else None,
        "season_apps":     ps["apps"] if ps else None,
        "player_note":     ps["note"] if ps else None,
        "is_top_scorer":   ps["note"] == "top scorer" if ps else False,
        "is_key_player":   ps is not None and ps.get("g",0) >= 5,
    }


def format_brief_for_display(match_brief, highlight_briefs):
    """Pretty-print the brief for user review."""
    mb = match_brief
    opp = mb["opponent"]
    result = f"Leverkusen {mb['lev_goals']}-{mb['opp_goals']} {opp}"
    xg_str = f"xG {mb['lev_xg']}-{mb['opp_xg']}" if mb['lev_xg'] else "no xG"

    print(f"\n{'='*65}")
    print(f"  COMMENTARY BRIEF: {result} ({xg_str}) | MD{mb['round']}")
    print(f"{'='*65}")

    print("\n📋 MATCH INTRO HOOKS:")
    if mb["ran_riot"]:       print("  🔥 Ran riot — won by 5+")
    if mb["easy_win"]:       print("  💪 Easy win — won by 4+")
    if mb["action_packed"]:  print("  ⚡ Action-packed — 5+ goals, tight margin")
    if mb["tight_game"]:     print("  😬 Tight game — few goals, 1-goal margin")
    if mb["ent_draw"]:       print("  🤝 Entertaining draw — 4+ goals")
    if mb["lev_drew"] and not mb["ent_draw"]: print("  😐 Goalless or tight draw")
    if mb["unbeaten_run"]:   print("  🏆 Final matchday — unbeaten all season!")
    if mb["title_clincher"]: print("  🥇 TITLE CLINCHER matchday")
    if mb["late_drama"]:     print("  ⏱️  Late drama — goal after 85'")
    if mb["early_goal"]:     print("  🚀 Early goal — before 15'")
    if mb["has_red_card"]:   print(f"  🟥 Red card — {mb['red_card_team']} (min {mb['red_minute']})")
    if mb["few_chances"]:    print(f"  🧱 Very few chances — Lev xG only {mb['lev_xg']}")
    if mb["dominant_xg"]:    print(f"  📊 Dominated xG: {mb['lev_xg']} vs {mb['opp_xg']}")
    if mb["brace_scorer"]:   print(f"  ⚽⚽ Brace: {', '.join(mb['brace_scorer'])}")
    if mb["hattrick"]:       print(f"  🎩 Hat-trick: {', '.join(mb['hattrick'])}")

    print("\n⚡ HIGHLIGHT BRIEFS:")
    for i, hb in enumerate(highlight_briefs, 1):
        if hb["type"] == "red_card":
            who = "OPPONENT" if hb["is_opponent_red"] else "LEVERKUSEN"
            print(f"  {i}. 🟥 RED CARD [{who}] {hb['player']} min {hb['minute']} | score: {hb['score_at']}", end="")
            if hb["early_red"]: print(" | ⚠️  early dismissal, changed the game", end="")
            print()
        else:
            tag = "⚽ GOAL" if hb["is_goal"] else f"💨 {hb['outcome']}"
            print(f"  {i}. {tag} | {hb['player']} min {hb['minute']} xG:{hb['xg']:.2f}", end="")
            flags = []
            if hb.get("is_opener"):      flags.append("match opener")
            if hb.get("is_equaliser"):   flags.append("Leverkusen equaliser")
            if hb.get("is_go_ahead"):    flags.append("Leverkusen go-ahead")
            if hb.get("is_consolation"): flags.append("CONSOLATION for opponent")
            if hb.get("opp_equaliser"):  flags.append("OPPONENT equalises")
            if hb.get("opp_takes_lead"): flags.append("OPPONENT takes lead")
            if hb["is_screamer"]:    flags.append("SCREAMER xG<0.05")
            if hb["is_low_xg_goal"]: flags.append("low-xG goal")
            if hb["is_high_xg_goal"]:flags.append("high-xG, dominant position")
            if hb.get("late_drama"):       flags.append("LATE DRAMA")
            if hb.get("brace"):            flags.append("BRACE (2nd goal)")
            if hb.get("hattrick_complete"):flags.append("HAT-TRICK COMPLETE!")
            if hb.get("hattrick_extend"):  flags.append("4th goal or more!")
            if hb["is_key_player"]:  flags.append(f"{hb['player_note']} ({hb['season_goals']}G)")
            if flags: print(f" | {' · '.join(flags)}", end="")
            print()
    print()


# ── Claude API call ───────────────────────────────────────────────────────────

_API_KEY = None   # cached after first entry

def call_claude(prompt, max_tokens=120):
    """Single API call to Claude Haiku — cheap and fast."""
    global _API_KEY
    if not _API_KEY:
        _API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not _API_KEY:
        _API_KEY = input("Paste your Anthropic API key (sk-ant-...): ").strip()
    resp = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": _API_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model":      MODEL,
            "max_tokens": max_tokens,
            "messages":   [{"role": "user", "content": prompt}]
        }
    )
    if resp.status_code != 200:
        print(f"    API error {resp.status_code}: {resp.text[:200]}")
        return ""
    data = resp.json()
    return data["content"][0]["text"].strip()


def ordinal(n):
    """Convert integer minute to ordinal string: 1 -> 1st, 2 -> 2nd, etc."""
    n = int(n)
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

def generate_intro(match_brief, mb_str):
    mb = match_brief
    opp = mb["opponent"]
    lev_g, opp_g = mb["lev_goals"], mb["opp_goals"]

    hooks_list = []
    if mb.get("unbeaten_run"):  hooks_list.append("This completes an entire Bundesliga season unbeaten — a historic first in German football")
    if mb.get("title_clincher"):hooks_list.append("This match clinches the Bundesliga title")
    if mb.get("ran_riot"):      hooks_list.append(f"Leverkusen ran riot, winning {lev_g}-{opp_g}")
    elif mb.get("tight_game"): hooks_list.append(f"A tight {lev_g}-{opp_g} win — Leverkusen had to dig deep")
    if mb.get("has_red_card"): hooks_list.append(f"{mb.get('red_card_team','a team')} reduced to ten men")
    if mb.get("hattrick"):     hooks_list.append(f"{mb['hattrick'][0]} completed a hat-trick")
    if mb.get("brace_scorer") and not mb.get("hattrick"):
        hooks_list.append(f"{mb['brace_scorer'][0]} bagged a brace")
    scorers = mb.get("lev_scorers", [])
    if scorers:
        hooks_list.append("goals from " + ", ".join(s.split()[-1] for s in scorers[:3]))
    hooks_str = "; ".join(hooks_list[:4]) if hooks_list else f"Leverkusen {lev_g}-{opp_g} {opp}"

    prompt = f"""You are directing a Bundesliga commentator using ElevenLabs Eleven v3 audio tags.
Write a match INTRODUCTION — 2 sentences — using these emotion direction tags:

Available tags: [calm, building] [quietly] [warmly] [EXCITED] [reverently] [pause]

STRICT FACTS:
- Result: Leverkusen {lev_g}-{opp_g} {opp}, Round {mb["round"]}
- Storylines: {hooks_str}
- Team nickname: Die Werkself
- Stadium: the BayArena

Sentence 1: Set the scene with calm authority — use [calm, building] or [quietly].
Sentence 2: One specific storyline — build emotion — end with [warmly] or [reverently] if historic.

Rules:
- Never say "xG"
- Never invent facts not in the storylines
- If unbeaten season: the ending MUST carry weight — use [reverently] or [pause]
- Max 50 words total including tags
- Tags count toward the word limit — use 2-3 maximum

Return ONLY the tagged commentary text. Nothing else."""
    return call_claude(prompt, max_tokens=150)



def generate_highlight(highlight_brief, match_brief, hb_str):
    htype    = highlight_brief["type"]
    mb       = match_brief
    lev_g    = mb["lev_goals"]
    opp_g    = mb["opp_goals"]
    opp_name = mb["opponent"]

    if htype == "red_card":
        hb  = highlight_brief
        who = "Leverkusen" if not hb["is_opponent_red"] else opp_name
        impact = "leaving Leverkusen a man down" if not hb["is_opponent_red"] else f"leaving {opp_name} with ten men"
        prompt = f"""Bundesliga commentator using ElevenLabs Eleven v3 audio tags.
ONE sentence (max 20 words) about this red card.

Available tags: [calm] [SHOCKED] [gasps] [quietly] [dramatically]

FACTS: {hb["player"]} ({who}) dismissed in minute {hb["minute"]}. Score: {hb["score_at"]}. {impact}.

Use [gasps] or [SHOCKED] at the moment. End with weight — [quietly] or [dramatically].
Return only the tagged sentence."""
        return call_claude(prompt, max_tokens=80)

    else:
        hb       = highlight_brief
        is_goal  = hb["is_goal"]
        player   = hb["player"]
        minute   = hb["minute"]
        minute_str = ordinal(minute)
        score    = hb["score_after"]
        xg       = hb["xg"]
        team     = hb["team"]

        # Parse score
        parts     = score.split("-") if "-" in score else ["0","0"]
        h_s, a_s  = int(parts[0]), int(parts[1])
        lev_score = h_s if mb["lev_home"] else a_s
        opp_score = a_s if mb["lev_home"] else h_s

        # Score before this goal
        if is_goal:
            if team == "Leverkusen":
                score_before = f"{lev_score-1}-{opp_score}" if mb["lev_home"] else f"{opp_score}-{lev_score-1}"
            else:
                score_before = f"{lev_score}-{opp_score-1}" if mb["lev_home"] else f"{opp_score-1}-{lev_score}"
        else:
            score_before = score

        # Narrative context
        if is_goal and team == "Leverkusen":
            if lev_score == 1 and opp_score == 0:
                moment = "opening goal — Leverkusen take the lead"
            elif lev_score > opp_score + 1:
                moment = f"making it {score} — Leverkusen in command"
            elif lev_score == opp_score + 1:
                moment = f"the winner — final score will be {lev_g}-{opp_g}"
            else:
                moment = f"goal for Leverkusen, score now {score}"
        elif is_goal and team != "Leverkusen":
            if opp_score > lev_score:
                moment = f"{opp_name} take the lead — but Leverkusen recover to win {lev_g}-{opp_g}"
            elif opp_score == lev_score:
                moment = f"{opp_name} equalise — but Leverkusen already lead {lev_g}-{opp_g} at full time"
            else:
                moment = f"consolation for {opp_name}, making it {score} — Leverkusen win {lev_g}-{opp_g}"
        else:
            moment = f"chance for {team}, score {score}"

        # xG position description
        shot_x   = float(hb.get("x") or 90)
        in_box   = shot_x > 84
        outside  = shot_x <= 84
        if xg > 0.60:    xg_desc = "clinical from close range — in a dominant position"
        elif xg > 0.30:  xg_desc = "a good chance in the penalty area"
        elif xg > 0.10:  xg_desc = "a difficult chance" if in_box else "a decent effort from range"
        elif xg > 0.05:  xg_desc = "a difficult angle inside the box" if in_box else "a speculative effort from distance"
        else:            xg_desc = "an improbable finish from a near-impossible angle" if in_box else "an audacious strike from well outside the box"

        # Player context
        ps = fd_to_sb(player)
        sb_ctx = hb.get("statsbomb_context", "")
        if ps:
            p_ctx = (f"{player}: {ps['note']}. "
                     f"IMPORTANT: {ps['g']} goals was their FINAL season total — "
                     f"use retrospective language: 'one of his {ps["g"]} for the campaign'.")
        else:
            p_ctx = f"{player}."

        # Milestone flags
        milestone = ""
        if hb.get("hattrick_complete"): milestone = "HAT-TRICK COMPLETE — this is the primary story, lead with it"
        elif hb.get("brace"):           milestone = "player's second goal of the night — mention brace"
        elif hb.get("hattrick_extend"): milestone = "fourth or fifth goal — extraordinary night"

        # ── MULTILINGUAL GOAL CRY ──────────────────────────────────────────
        goal_cry, goal_lang, goal_flag = get_goal_cry(player)

        # Build the language instruction
        if goal_lang == "German":
            lang_instruction = f'After the English goal call, use the German: "{goal_cry}" — this is the Bundesliga home language'
            lang_instruction = f"After the English call, add \"{goal_cry}\" — the language of this player's footballing soul"
            lang_instruction = f"After the English call, add \"{goal_cry}\" — celebrating in the player's Nigerian heritage"
        elif goal_lang == "French":
            lang_instruction = f'After the English call, add "{goal_cry}" — French flair for a French player'
        elif goal_lang == "Dutch":
            lang_instruction = f'After the English call, add "{goal_cry}" — Dutch football culture'
        elif goal_lang == "Czech":
            lang_instruction = f'After the English call, add "{goal_cry}" — celebrating in Czech'
        elif goal_lang == "Croatian":
            lang_instruction = f'After the English call, add "{goal_cry}" — Croatian passion'
        else:
            lang_instruction = f'After the English call, add "{goal_cry}"'

        # ── HISTORIC SEASON ENDING ─────────────────────────────────────────
        is_last_match = mb.get("unbeaten_run", False)
        if is_last_match and mb.get("round") == 34:
            ending_instruction = ('IMPORTANT: This is the final matchday of the unbeaten season. '
                                  'End with [reverently] and a single phrase about history. '
                                  'Example: [reverently] Ungeschlagen. Unbeaten. Forever.')
        else:
            ending_instruction = 'End with [warmly] and a brief reflection connecting to the season story.'

        prompt = f"""You are directing a Bundesliga commentator performance using ElevenLabs Eleven v3 audio tags.
Write ONE commentary sequence (max 35 words) for this {"GOAL" if is_goal else "shot"}.

AVAILABLE AUDIO TAGS:
- [calm, building] — pre-goal tension, quiet anticipation
- [EXCITED] — accelerating toward the moment
- [SHOUTING] — the goal cry itself (loudest point)
- [crowd cheering] — place ONCE after the goal cry
- [pause] — a beat of silence (use ... or [pause])
- [warmly] — joy and celebration
- [reverently] — historic weight, quiet significance
- [gasps] — near miss or shock

STRUCTURE for a goal:
1. [calm, building] — one phrase of anticipation (optional but powerful)
2. [EXCITED] — the approach
3. [SHOUTING] GOAAAAAL! {goal_cry} [crowd cheering]
4. [pause]
5. [warmly] or [reverently] — the reflection

STRICT FACTS:
- Player: {player} ({team})
- Minute: the {minute_str}
- Score: {score_before} → {score}
- Final score: Leverkusen {lev_g}-{opp_g} {opp_name}
- This moment: {moment}
- Shot quality: {xg_desc}
- {p_ctx}
{f"- Milestone: {milestone}" if milestone else ""}
{f"- Shot context: {sb_ctx}" if sb_ctx else ""}

MULTILINGUAL INSTRUCTION:
{lang_instruction}

{ending_instruction}

STYLE RULES:
- Never say "xG"
- Never invent facts
- The goal cry must be the loudest, most extended moment
- After the goal cry, always drop in energy — warmth or reverence
- Peter Drury style: lyrical, specific, not generic
- {"This is an OPPONENT goal — be accurate about who scored and what it means" if team != "Leverkusen" else ""}

Return ONLY the tagged commentary text. No preamble."""

        return call_claude(prompt, max_tokens=120)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match",   type=str, default=None, help="Filter by opponent name")
    parser.add_argument("--preview",    action="store_true", help="Show briefs only, no API calls")
    parser.add_argument("--regenerate", action="store_true", help="Overwrite existing commentary")
    args = parser.parse_args()

    # Load caches
    shots_path  = f"{CACHE_DIR}/shots.csv"
    events_path = f"{CACHE_DIR}/events_key.csv"
    xg_path     = f"{CACHE_DIR}/xg_by_match.csv"
    matches_path= f"{CACHE_DIR}/matches.csv"

    for p in [shots_path, events_path, xg_path, matches_path]:
        if not os.path.exists(p):
            print(f"ERROR: {p} not found. Run cache scripts first.")
            return

    shots_all  = pd.read_csv(shots_path)
    events_all = pd.read_csv(events_path)
    xg_all     = pd.read_csv(xg_path)
    matches    = pd.read_csv(matches_path)

    # Load existing commentary to avoid regenerating
    if os.path.exists(OUT_CSV):
        existing = pd.read_csv(OUT_CSV)
    else:
        existing = pd.DataFrame()

    # If regenerating a specific match, remove its old rows first
    if args.regenerate and args.match and not existing.empty:
        mask = (
            existing["home_fd"].str.contains(args.match, case=False, na=False) |
            existing["away_fd"].str.contains(args.match, case=False, na=False)
        )
        existing = existing[~mask].copy()
        print(f"  Cleared existing commentary for matches containing '{args.match}'.")

    done_keys = set(zip(existing["home_fd"], existing["away_fd"])) if not existing.empty else set()

    # Filter matches
    # Deduplicate: StatsBomb stores each match once with a fixed match_id
    # but our matches.csv may have both directions — keep unique match_ids only
    lev_matches = matches[
        (matches["home_fd"]=="Leverkusen") | (matches["away_fd"]=="Leverkusen")
    ].drop_duplicates(subset=["match_id"]).copy()

    if args.match:
        lev_matches = lev_matches[
            lev_matches["home_fd"].str.contains(args.match, case=False) |
            lev_matches["away_fd"].str.contains(args.match, case=False)
        ]

    # Need to know rounds — load football-data if available
    try:
        import polars as pl
        fd = pl.read_csv(
            "https://www.football-data.co.uk/mmz4281/2324/D1.csv",
            infer_schema_length=0
        ).with_columns(
            pl.col("Date").str.strptime(pl.Date, format="%d/%m/%Y", strict=False)
        ).sort("Date").with_row_index("_i").with_columns(
            ((pl.col("_i") // 9) + 1).cast(pl.Int32).alias("Round")
        ).to_pandas()
        round_lookup = {}
        for _, r in fd.iterrows():
            round_lookup[(r["HomeTeam"], r["AwayTeam"])] = int(r["Round"])
    except Exception:
        round_lookup = {}

    new_rows = []
    total = len(lev_matches)

    for i, (_, m) in enumerate(lev_matches.iterrows(), 1):
        home, away = m["home_fd"], m["away_fd"]
        mid = m["match_id"]
        key = (home, away)

        if key in done_keys and not args.match and not args.regenerate:
            print(f"  [{i}/{total}] {home} vs {away} — already done, skipping")
            continue

        print(f"\n  [{i}/{total}] {home} vs {away}")

        # Get round
        match_round = round_lookup.get((home, away),
                      round_lookup.get((away, home), 0))

        # Filter shot/event data for this match
        shots_m  = shots_all[
            ((shots_all["home_fd"]==home) & (shots_all["away_fd"]==away)) |
            ((shots_all["home_fd"]==away) & (shots_all["away_fd"]==home))
        ].copy()
        if shots_m["match_id"].nunique() > 1:
            shots_m = shots_m[shots_m["match_id"]==shots_m["match_id"].iloc[0]]

        events_m = events_all[
            ((events_all["home_fd"]==home) & (events_all["away_fd"]==away)) |
            ((events_all["home_fd"]==away) & (events_all["away_fd"]==home))
        ].copy()

        # Build briefs
        match_brief = build_match_brief(home, away, shots_m, events_m, xg_all, match_round)
        mb_str      = json.dumps({k:v for k,v in match_brief.items()
                                  if k not in ("scorer_context",)},
                                 indent=2, default=str)

        # Get highlight sequence
        from shot_loader import get_shot_sequence
        from xg_loader   import get_key_events
        shot_seq   = get_shot_sequence(home, away)
        rc_events  = get_key_events(home, away)["red_cards"]

        # Build score_at for red cards
        shot_scores = sorted([(s["minute"], s["score_after"]) for s in shot_seq], key=lambda x: x[0])
        def score_at(minute):
            last = "0-0"
            for mm, sc in shot_scores:
                if mm <= minute: last = sc
                else: break
            return last

        rc_items   = [{"type":"red_card","minute":r["minute"],"player":r["player"],
                       "team_fd":r["team_fd"],"score_at":score_at(r["minute"])} for r in rc_events]
        shot_items = [{**s,"type":"shot"} for s in shot_seq]
        combined   = sorted(shot_items + rc_items, key=lambda x: x["minute"])

        # Look up match_id for context enrichment
        _mid = get_match_id_for_teams(home, away)

        # Track per-player goal count for this match (for brace/hattrick milestone logic)
        player_goal_counts = {}
        highlight_briefs = []
        for h in combined:
            if h.get("type") == "shot" and h.get("is_goal") == 1 and h.get("team_fd") == "Leverkusen":
                p = h.get("player", "")
                player_goal_counts[p] = player_goal_counts.get(p, 0) + 1
                num = player_goal_counts[p]
            else:
                num = 1
            hb = build_highlight_brief(h, match_brief, player_goal_num=num)
            # Enrich with StatsBomb event context (set piece, technique, assist)
            if _mid and h.get("type") == "shot":
                ctx = enrich_shot_context(_mid, h.get("player",""), h.get("minute", 0))
                hb["statsbomb_context"] = build_context_flags(ctx)
                if ctx:
                    hb["technique"]    = ctx.get("technique","")
                    hb["assist_player"]= ctx.get("assist_player","")
                    hb["cross_assist"] = ctx.get("cross_assist", False)
                    hb["shot_type"]    = ctx.get("shot_type","Open Play")
                    hb["play_pattern"] = ctx.get("play_pattern","")
            else:
                hb["statsbomb_context"] = ""
            highlight_briefs.append(hb)

        # Display brief for review
        format_brief_for_display(match_brief, highlight_briefs)

        if args.preview:
            continue

        confirm = input(f"  Generate commentary for {home} vs {away}? (y/n/q): ").strip().lower()
        if confirm == "q":
            break
        if confirm != "y":
            print("  Skipped.")
            continue

        # Generate intro
        print("  Generating intro...", end="", flush=True)
        intro_text = generate_intro(match_brief, mb_str)
        print(" done")

        # Generate per-highlight
        for j, (h, hb) in enumerate(zip(combined, highlight_briefs)):
            hb_str = json.dumps(hb, indent=2, default=str)
            print(f"  Generating highlight {j+1}/{len(combined)}...", end="", flush=True)
            text = generate_highlight(hb, match_brief, hb_str)
            print(f" done")

            player = h.get("player","")
            new_rows.append({
                "home_fd":      home,
                "away_fd":      away,
                "match_round":  match_round,
                "content_type": "highlight",
                "highlight_idx": j,
                "player":       player,
                "minute":       h["minute"],
                "is_goal":      h.get("is_goal", 0),
                "event_type":   h.get("type","shot"),
                "commentary":   text,
            })
            time.sleep(0.3)

        new_rows.append({
            "home_fd":      home,
            "away_fd":      away,
            "match_round":  match_round,
            "content_type": "intro",
            "highlight_idx": -1,
            "player":       "",
            "minute":       0,
            "is_goal":      0,
            "event_type":   "intro",
            "commentary":   intro_text,
        })
        print(f"\n  INTRO: {intro_text}\n")

    # Save
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        combined_df = pd.concat([existing, new_df], ignore_index=True) if not existing.empty else new_df
        combined_df.to_csv(OUT_CSV, index=False)
        print(f"\n✓ Saved {len(new_rows)} new rows to {OUT_CSV}")
    else:
        print("\nNo new commentary generated.")


if __name__ == "__main__":
    main()
