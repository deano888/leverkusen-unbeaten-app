"""
app.py  -  Bundesliga 2023/24  -  Phase 2
Dark theme · Bundesliga palette · centred 60% layout · team badges
"""

import time
import streamlit as st
import polars as pl
from data_loader import load_data, get_available_rounds
from badges import badge_svg
from xg_loader import build_xg_lookup, get_match_xg, get_players, get_key_events
from shot_loader import get_shot_sequence, get_all_shots_for_commentary as get_all_shots
from voice_loader import play_audio, has_audio, get_audio_duration
import json

st.set_page_config(
    page_title="Bundesliga 2023/24",
    page_icon="🇩🇪",          # German flag
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap');

html, body, [class*="css"] {
    font-family: 'Bitter', serif;
    background-color: #080810 !important;
    color: #c8c8d8;
}
.stApp { background-color: #080810 !important; }

.block-container {
    padding-top: 1.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}

/* ── Header ── */
.dash-header {
    width: 62%;
    margin: 0 auto 14px auto;
    background: linear-gradient(105deg, #d20515 0%, #a80010 55%, #200005 100%);
    border-radius: 8px;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 2px 24px rgba(210,5,21,.22), 0 0 80px rgba(210,5,21,.04);
    border: 1px solid rgba(210,5,21,.25);
    position: relative;
    overflow: hidden;
}
.dash-header::after {
    content: '';
    position: absolute; right: -30px; top: -30px;
    width: 130px; height: 130px;
    background: rgba(255,200,0,.05);
    border-radius: 50%;
}
.dash-header h1 {
    font-family: 'Bitter', serif;
    font-size: 1.4rem; font-weight: 800; color: #fff;
    margin: 0; letter-spacing: 2px; text-transform: uppercase;
}
.about-btn {
    background: transparent;
    border: 1px solid rgba(255,200,0,.45);
    color: #ffc800;
    font-family: 'Bitter', serif;
    font-size: .7rem; font-weight: 700;
    padding: 5px 14px; border-radius: 20px;
    letter-spacing: 1px; text-transform: uppercase;
    cursor: pointer; margin-left: auto;
    transition: all .2s;
    text-decoration: none;
    display: inline-flex; align-items: center; gap: 6px;
}
.about-btn:hover {
    background: rgba(255,200,0,.15);
    border-color: #ffc800;
    color: #fff;
    box-shadow: 0 0 12px rgba(255,200,0,.3);
}
.back-btn {
    background: rgba(255,200,0,.12);
    border: 1px solid rgba(255,200,0,.5);
    color: #ffc800;
    font-family: 'Bitter', serif;
    font-size: .7rem; font-weight: 700;
    padding: 5px 14px; border-radius: 20px;
    letter-spacing: 1px; text-transform: uppercase;
    cursor: pointer; margin-left: auto;
    transition: all .2s;
}
.season-pill {
    background: rgba(255,200,0,.13);
    border: 1px solid rgba(255,200,0,.32);
    color: #ffc800;
    font-family: 'Bitter', serif;
    font-size: .72rem; font-weight: 700;
    padding: 2px 10px; border-radius: 20px;
    letter-spacing: 1px; text-transform: uppercase;
    margin-left: auto; z-index: 1;
}

/* ── Round badge ── */
.round-badge {
    background: linear-gradient(135deg, #d20515, #a00010);
    color: #fff;
    font-family: 'Bitter', serif;
    font-weight: 700; font-size: .82rem;
    padding: 3px 11px; border-radius: 20px;
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(210,5,21,.4);
}

/* ── Match rows ── */
.mrow {
    background: #0e0e1c;
    border: 1px solid #181830;
    border-left: 3px solid #181830;
    border-radius: 7px;
    padding: 7px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 5px;
    transition: border-color .18s, background .18s, box-shadow .18s;
    line-height: 1;
}
.mrow:hover {
    border-color: #d20515;
    border-left-color: #d20515;
    background: #12121f;
    box-shadow: 0 2px 18px rgba(210,5,21,.1);
}
.mdate { color: #7070a0; font-size: .66rem; width: 72px; flex-shrink: 0; }
.mteam {
    font-family: 'Bitter', serif;
    font-weight: 600; font-size: .93rem; color: #d0d0e8;
    flex: 1; text-align: center; letter-spacing: .3px;
}
.mscore {
    font-family: 'Bitter', serif;
    font-size: 1.18rem; font-weight: 800; color: #fff;
    background: #080812;
    border: 1px solid #1e1e38;
    border-radius: 5px;
    padding: 4px 15px; min-width: 68px; text-align: center;
    letter-spacing: 1px;
}
.rbadge {
    font-size: .58rem; font-weight: 700; letter-spacing: .8px;
    padding: 2px 6px; border-radius: 3px; text-transform: uppercase; flex-shrink: 0;
}
.rH { background:rgba(93,186,93,.1); color:#5dba5d; border:1px solid rgba(93,186,93,.22); }
.rA { background:rgba(210,5,21,.1);  color:#e05050; border:1px solid rgba(210,5,21,.22); }
.rD { background:rgba(255,200,0,.08); color:#ffc800; border:1px solid rgba(255,200,0,.18); }

/* ── Stats button ── */
div[data-testid="column"] .stButton > button {
    font-size: .7rem !important;
    font-family: 'Bitter', serif !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    padding: 4px 11px !important;
    height: auto !important;
    border-radius: 5px !important;
    background: linear-gradient(135deg, #d20515, #a00010) !important;
    color: #ffc800 !important;
    border: 1px solid rgba(255,200,0,.28) !important;
    min-height: unset !important;
    box-shadow: 0 2px 8px rgba(210,5,21,.28) !important;
    transition: all .15s !important;
}
div[data-testid="column"] .stButton > button:hover {
    background: linear-gradient(135deg, #ff1a28, #d20515) !important;
    color: #fff !important;
    border-color: #ffc800 !important;
    box-shadow: 0 3px 14px rgba(210,5,21,.5) !important;
}

/* ── Selectbox ── */
div[data-testid="stSelectbox"] > div > div {
    background: #0e0e1c !important;
    border: 1px solid #1e1e38 !important;
    border-radius: 6px !important;
    color: #c8c8d8 !important;
}
div[data-testid="stSelectbox"] > div > div:hover { border-color: #d20515 !important; }

/* ── Progress bar ── */
div[data-testid="stProgressBar"] > div { background: #1c1c35 !important; }
div[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #d20515, #ff6020) !important;
}
hr { border-color: #181830 !important; }
/* ── View tabs ──────────────────────────────────────────────────────────── */
.view-tabs { display:flex; gap:6px; margin:14px auto 10px; width:62%; }
.vtab {
    flex:1; text-align:center; padding:7px 0;
    border-radius:8px; cursor:pointer;
    font-size:.72rem; font-weight:700; letter-spacing:.8px;
    text-transform:uppercase;
    background:#0e0e1c; border:1px solid #1a1a32; color:#555570;
    transition: all .2s;
}
.vtab.active {
    background:#d20515; border-color:#d20515; color:#fff;
    box-shadow: 0 0 10px rgba(210,5,21,.3);
}

/* ── League Table ──────────────────────────────────────────────────────── */
.league-table { width:100%; border-collapse:collapse; margin-top:8px; }
.league-table th {
    font-size:.6rem; color:#555570; text-transform:uppercase;
    letter-spacing:.8px; padding:5px 8px; border-bottom:1px solid #1a1a32;
    text-align:center;
}
.league-table th:first-child { text-align:left; padding-left:10px; }
.league-table td {
    font-size:.8rem; color:#c8c8e0; padding:6px 8px;
    border-bottom:1px solid #0e0e1c; text-align:center;
}
.league-table td:first-child { text-align:left; padding-left:10px; }
.league-table tr:hover td { background:#0e0e1c; }
.lev-row td { color:#fff !important; font-weight:700; }
.lev-row td:nth-child(2) { color:#ffc800 !important; }
.pos-num { color:#555570; font-size:.72rem; margin-right:6px; }
.pts-cell { color:#d20515 !important; font-weight:800; font-size:.88rem; }
.gd-pos { color:#60c878; }
.gd-neg { color:#e05050; }

/* ── Top Scorers ────────────────────────────────────────────────────────── */
.scorer-table { width:100%; border-collapse:collapse; margin-top:8px; }
.scorer-table th {
    font-size:.6rem; color:#555570; text-transform:uppercase;
    letter-spacing:.8px; padding:5px 8px; border-bottom:1px solid #1a1a32;
}
.scorer-table th:first-child { text-align:center; width:40px; }
.scorer-table th:nth-child(2) { text-align:left; }
.scorer-table td {
    font-size:.8rem; color:#c8c8e0; padding:6px 8px;
    border-bottom:1px solid #0e0e1c;
}
.scorer-table td:first-child { text-align:center; color:#555570; font-size:.72rem; }
.scorer-goals { color:#d20515; font-weight:800; font-size:.95rem; text-align:right; }
.scorer-lev td:nth-child(2) { color:#fff; font-weight:700; }
.scorer-lev .scorer-goals { color:#ffc800; }

/* ── Chatbot ─────────────────────────────────────────────────────────────── */
.chat-wrap { margin-top: 18px; border-top: 1px solid #1a1a32; padding-top: 14px; }
.chat-label { font-size:.6rem; color:#9090b8; text-transform:uppercase;
              letter-spacing:1px; margin-bottom:8px; }
.chat-bubble-user { background:#1a1a32; border-radius:10px 10px 2px 10px;
    padding:8px 12px; margin:6px 0; font-size:.82rem; color:#c8c8e0;
    max-width:85%; margin-left:auto; text-align:right; }
.chat-bubble-bot { background:#0e0e1c; border:1px solid #1a1a32;
    border-radius:10px 10px 10px 2px; padding:8px 12px; margin:6px 0;
    font-size:.82rem; color:#e0e0f0; max-width:92%; }
.chat-tier { font-size:.6rem; color:#555570; margin-top:3px; }
.suggest-btn { display:inline-block; margin:3px; padding:3px 9px;
    background:#0e0e1c; border:1px solid #2a2a4a; border-radius:12px;
    font-size:.68rem; color:#9090b8; cursor:pointer; }

/* ── MOBILE RESPONSIVE ─────────────────────────────────────────────── */
@media (max-width: 768px) {

    /* Header */
    .dash-header h1 { font-size: 1.1rem !important; }

    /* Match rows — stack better on small screens */
    .mteam { font-size: .75rem !important; }
    .mscore { font-size: 1.1rem !important; padding: 4px 10px !important; }

    /* Dialog — full width on mobile */
    div[data-testid="stModal"] > div {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        border-radius: 0 !important;
    }

    /* Shot map SVG — scale down */
    svg { max-width: 100% !important; height: auto !important; }

    /* About page grid — single column */
    .ab-grid {
        grid-template-columns: 1fr !important;
    }

    /* Stats grid — 3 columns instead of 5 */
    .ab-stats { flex-wrap: wrap !important; }
    .ab-stat { min-width: 30% !important; }

    /* Shot card — constrain width */
    div[style*="width:560px"] {
        width: 100% !important;
        max-width: 560px !important;
    }
}


/* Crush column gaps inside dialog */
div[data-testid="stModal"] div[data-testid="stHorizontalBlock"] {
    gap: 0.2rem !important;
}
div[data-testid="stModal"] div[data-testid="column"] {
    padding-left: 0.2rem !important;
    padding-right: 0.2rem !important;
    min-width: 0 !important;
}
div[data-testid="stModal"] div[data-testid="stMarkdownContainer"] {
    padding: 0 !important;
}
/* ── Score + xG stacked ── */
.mscore-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
}
.xg-wrap {
    display: flex;
    align-items: center;
    gap: 4px;
}
.xg-label {
    font-size: .5rem;
    color: #2a2a48;
    text-transform: uppercase;
    letter-spacing: .8px;
    font-weight: 700;
}
.xg-values {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: 'Bitter', serif;
    font-weight: 600;
    font-size: .72rem;
    color: #6060a0;
}
.xg-sep { color: #222240; }
.xg-na  { font-size: .6rem; color: #1e1e35; }

</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def si(val):
    try: return max(int(float(val)), 0)
    except: return 0

def sf(val, d=2):
    try: return f"{float(val):.{d}f}"
    except: return "—"

def result_of(fthg, ftag):
    if fthg > ftag: return "H"
    if ftag > fthg: return "A"
    return "D"





def show_about():
    """Render the About page — all in one markdown call to preserve CSS classes."""
    st.markdown("""
<style>
.ab-wrap { max-width: 860px; margin: 0 auto; padding: 8px 0 40px; }
.ab-sec {
    background: #0e0e1c; border: 1px solid #1a1a32;
    border-radius: 10px; padding: 28px 32px; margin-bottom: 18px;
}
.ab-sec-red  { border-left: 3px solid #d20515;
               background: linear-gradient(135deg,#0e0e1c,#12081a); }
.ab-sec-gold { border-left: 3px solid #ffc800; }
.ab-label {
    font-size: .55rem; font-weight: 700; color: #d20515;
    text-transform: uppercase; letter-spacing: 1.6px; margin-bottom: 8px;
}
.ab-h2 {
    font-family: Bitter,serif; font-size: 1.35rem; font-weight: 800;
    color: #f0f0f0; margin: 0 0 14px; letter-spacing: .5px;
}
.ab-p { font-size: .82rem; color: #9090b8; line-height: 1.75; margin: 0 0 10px; }
.ab-p em   { color: #ffc800; font-style: normal; font-weight: 600; }
.ab-p strong { color: #f0f0f0; }
.ab-div { height: 1px; background: #1a1a32; margin: 18px 0; }
.ab-stats { display: flex; gap: 0; margin: 20px 0 4px; border: 1px solid #1a1a32; border-radius: 8px; overflow: hidden; }
.ab-stat { flex: 1; text-align: center; padding: 14px 6px; border-right: 1px solid #1a1a32; }
.ab-stat:last-child { border-right: none; }
.ab-num { font-family: Bitter,serif; font-size: 1.6rem; font-weight: 800; color: #d20515; }
.ab-lbl { font-size: .52rem; color: #9090b8; text-transform: uppercase; letter-spacing: .8px; margin-top: 3px; }
.ab-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.ab-tech-h { font-size: .8rem; font-weight: 700; color: #f0f0f0; margin: 0 0 5px; }
.ab-tech-p { font-size: .75rem; color: #7070a0; line-height: 1.65; margin: 0; }
.ab-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
.ab-pill {
    font-size: .65rem; font-weight: 700; letter-spacing: .5px;
    padding: 4px 12px; border-radius: 20px; text-transform: uppercase;
}
.p-red   { background:rgba(210,5,21,.15);   color:#e05050; border:1px solid rgba(210,5,21,.3);   }
.p-gold  { background:rgba(255,200,0,.1);   color:#ffc800; border:1px solid rgba(255,200,0,.25); }
.p-blue  { background:rgba(80,120,220,.12); color:#7090e0; border:1px solid rgba(80,120,220,.25); }
.p-green { background:rgba(60,180,100,.1);  color:#60c878; border:1px solid rgba(60,180,100,.25); }
.ab-link { color: #ffc800; text-decoration: none; font-weight: 600; font-size: .82rem; }
.ab-footer { text-align:center; padding:20px 0 8px; color:#333355; font-size:.6rem; line-height:1.7; }
.ab-footer a { color:#555577; }
</style>

<div class="ab-wrap">

  <div class="ab-sec ab-sec-red">
    <div class="ab-label">The Story</div>
    <div class="ab-h2">Re-living a Historic Season</div>
    <p class="ab-p">In 2023/24, <em>Bayer Leverkusen</em> did something incredible — they played
    <strong>34 Bundesliga matches and did not lose a single one</strong>, becoming the first
    German side ever to go an entire top-flight season unbeaten and win the title.</p>
    <p class="ab-p">By combining <strong>StatsBomb open data</strong>, <strong>human analytical
    logic</strong> and <strong>AI-generated commentary</strong>, this app brings every goal,
    red card and moment of brilliance back to life — with added voice, shot maps and match stats
    for the final 10 decisive matchdays of that remarkable campaign.</p>
    <p class="ab-p" style="margin:0;">A huge congratulations to <em>Bayer Leverkusen</em>
    and <em>Bravo to StatsBomb</em> for releasing their rich event data freely to the world.</p>
    <div class="ab-stats">
      <div class="ab-stat"><div class="ab-num">34</div><div class="ab-lbl">Unbeaten games</div></div>
      <div class="ab-stat"><div class="ab-num">89</div><div class="ab-lbl">Goals scored</div></div>
      <div class="ab-stat"><div class="ab-num">24</div><div class="ab-lbl">Wins</div></div>
      <div class="ab-stat"><div class="ab-num">10</div><div class="ab-lbl">Draws</div></div>
      <div class="ab-stat"><div class="ab-num">0</div><div class="ab-lbl">Defeats</div></div>
    </div>
  </div>

  <div class="ab-sec">
    <div class="ab-label">Data Sources</div>
        <p class="ab-p"><strong>StatsBomb Open Data</strong> provides rich event-level football
    data — every shot, pass, dribble and tackle captured with x/y coordinates, xG values and
    player-level detail. Their free Bundesliga 2023/24 dataset powers every shot map, xG
    figure and player stat in this app.</p>
    <p class="ab-p"><a href="https://github.com/statsbomb/open-data" target="_blank" class="ab-link">→ statsbomb.com / open-data on GitHub</a></p>
    <div class="ab-div"></div>
    <p class="ab-p"><strong>football-data.co.uk</strong> supplies historical match results,
    odds and league tables for all major European divisions. Match results, half-time scores
    and betting odds in this app are sourced from their freely available CSV datasets.</p>
    <p class="ab-p" style="margin:0;"><a href="https://www.football-data.co.uk" target="_blank" class="ab-link">→ football-data.co.uk</a></p>
  </div>

  <div class="ab-sec">
    <div class="ab-label">Technology</div>
    <div class="ab-h2">How It's Built</div>
    <p class="ab-p">Built entirely in <strong>Python</strong>, combining a modern data pipeline
    with AI generation and interactive visualisation.</p>
    <div class="ab-div"></div>
    <div class="ab-grid">
      <div>
        <p class="ab-tech-h">🖥️ Streamlit</p>
        <p class="ab-tech-p">The entire dashboard — match rows, animated stat popups and shot
        map sequences — is a Streamlit web app. Fast, Pythonic, beautiful.</p>
      </div>
      <div>
        <p class="ab-tech-h">🤖 Claude AI (Anthropic)</p>
        <p class="ab-tech-p">Match introductions and highlight commentary generated by Claude,
        guided by 25+ contextual flags — scorelines, player stats and match narrative hooks.</p>
      </div>
      <div>
        <p class="ab-tech-h">🎙️ ElevenLabs</p>
        <p class="ab-tech-p">AI commentary converted to natural-sounding speech via ElevenLabs
        TTS, with a custom voice trained for football broadcast style.</p>
      </div>
      <div>
        <p class="ab-tech-h">📊 StatsBombPy + Pandas</p>
        <p class="ab-tech-p">StatsBomb event data processed into xG, shot maps, player minutes
        and key events, cached as CSV for instant playback.</p>
      </div>
    </div>
    <div class="ab-pills">
      <span class="ab-pill p-red">Python</span>
      <span class="ab-pill p-gold">Streamlit</span>
      <span class="ab-pill p-blue">Claude AI</span>
      <span class="ab-pill p-green">ElevenLabs</span>
      <span class="ab-pill p-red">StatsBombPy</span>
      <span class="ab-pill p-gold">Pandas</span>
      <span class="ab-pill p-blue">SVG Visualisation</span>
      <span class="ab-pill p-green">REST APIs</span>
    </div>
  </div>

  <div class="ab-sec ab-sec-gold">
    <div class="ab-label">The Builder</div>
        <p class="ab-p">I'm an experienced <strong>data analyst</strong> with a passion for bringing data to life — by making it useful and beautiful.</p>
    <p class="ab-p">This project combines many of my interests — sports analytics, AI integration, and building tools that make complex data accessible and exciting. And it's great fun to relive this unique Leverkusen achievement.</p>
    <p class="ab-p" style="margin:0;">If you're interested in data analytics, sports data,
    or just want to talk football — I'd love to hear from you.</p>
    <div style="margin-top:16px;">
      <a href="https://www.linkedin.com/in/deanoshaddick/" target="_blank" class="ab-link">🔗 Dean Shaddick — LinkedIn</a>
    </div>
  </div>

  <div class="ab-footer">
    Data provided by <strong>StatsBomb</strong> under their
    <a href="https://github.com/statsbomb/open-data" target="_blank">Open Data licence</a>
    and <strong>football-data.co.uk</strong>.<br>
    This project is for educational and portfolio purposes only.
    All team names and competition names are property of their respective owners.
  </div>

</div>
""", unsafe_allow_html=True)

@st.dialog("Match Summary", width="large")
def show_match_dialog(row):
    home = row["HomeTeam"];  away = row["AwayTeam"]
    dialog_key = f"{home}_{away}_{int(time.time()*100)%100000}"
    fthg = si(row["FTHG"]); ftag = si(row["FTAG"])
    hthg = si(row["HTHG"]); htag = si(row["HTAG"])
    hs   = si(row["HS"]);   a_s  = si(row["AS"])
    hst  = si(row["HST"]);  ast  = si(row["AST"])
    hc   = si(row["HC"]);   ac   = si(row["AC"])
    hy   = si(row["HY"]);   ay   = si(row["AY"])
    hr   = si(row["HR"]);   ar   = si(row["AR"])
    rh   = sf(row["match_resultH"])
    rx   = sf(row["match_resultX"])
    ra   = sf(row["match_resultA"])
    res  = result_of(fthg, ftag)

    hbadge = badge_svg(home, 40)
    abadge = badge_svg(away, 40)

    # Load StatsBomb data only for Leverkusen games from round 25+
    row_round  = row.get("Round", 0) if isinstance(row, dict) else 0
    use_sb     = ("Leverkusen" in (home, away)) and (int(row_round) >= 25)
    players    = get_players(home, away)    if use_sb else {}
    key_events = get_key_events(home, away) if use_sb else {"goals":[],"red_cards":[]}
    shots_seq  = get_shot_sequence(home, away) if use_sb else []
    hxg, axg   = get_match_xg(_cached_xg(), home, away) if use_sb else (None, None)
    has_sb     = bool(players)

    # Build combined highlight sequence: shots + red cards sorted by minute
    rc_events = key_events.get("red_cards", [])
    # Add score_at to each red card by finding score just before that minute in shots
    shot_scores = sorted([(s["minute"], s["score_after"]) for s in get_all_shots(home, away)], key=lambda x: x[0])
    def score_at_minute(minute):
        last = "0-0"
        for m, s in shot_scores:
            if m <= minute: last = s
            else: break
        return last
    rc_items = [{"type":"red_card","minute":r["minute"],"player":r["player"],
                 "team_fd":r["team_fd"],"score_at":score_at_minute(r["minute"])}
                for r in rc_events]
    shot_items = [{**s, "type":"shot"} for s in shots_seq]
    combined_seq = sorted(shot_items + rc_items, key=lambda x: x["minute"])

    goals_by_player = {}
    reds_by_player  = {}
    for g in key_events.get("goals", []):
        goals_by_player.setdefault(g["player"], []).append(g["minute"])
    for r in key_events.get("red_cards", []):
        reds_by_player[r["player"]] = r["minute"]

    # ── HEADER: badges + score + HT + compact odds ────────────────────────────

    if use_sb and hxg is not None and axg is not None:
        xg_left  = f"{hxg:.2f}"
        xg_mid   = "xG"
        xg_right = f"{axg:.2f}"
    else:
        xg_left  = ""
        xg_mid   = f"HT {hthg} – {htag}"
        xg_right = ""
    home_xg_display = f"{xg_left} {xg_mid} {xg_right}".strip()

    st.markdown(f"""
    <div style="text-align:center;margin-bottom:10px;">
        <div style="display:flex;align-items:center;justify-content:center;gap:20px;margin-bottom:6px;">
            <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:110px;">
                {hbadge}
                <span style="font-size:.75rem;font-weight:700;color:#555570;letter-spacing:.8px;text-transform:uppercase;">{home}</span>
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
                <div style="font-size:.5rem;color:#888;text-transform:uppercase;letter-spacing:.8px;">Full Time</div>
                <div style="display:flex;align-items:center;justify-content:center;gap:8px;">
                    <span style="font-family:'Bitter',serif;font-size:2.4rem;font-weight:800;color:#111122;line-height:1.1;">{fthg}</span>
                    <div style="display:flex;flex-direction:column;align-items:center;gap:1px;">
                        <span style="font-family:'Bitter',serif;font-size:2.4rem;font-weight:800;color:#111122;line-height:1;">–</span>
                        <div style="display:flex;align-items:center;gap:3px;white-space:nowrap;font-size:.55rem;color:#aaa;">
                            <span style="letter-spacing:.3px;">{xg_left}</span>
                            <span style="font-size:.46rem;color:#bbb;text-transform:uppercase;letter-spacing:.6px;font-weight:700;">{xg_mid}</span>
                            <span style="letter-spacing:.3px;">{xg_right}</span>
                        </div>
                    </div>
                    <span style="font-family:'Bitter',serif;font-size:2.4rem;font-weight:800;color:#111122;line-height:1.1;">{ftag}</span>
                </div>
                <div style="display:flex;gap:3px;margin-top:5px;">
                    <div style="text-align:center;background:#e8e8ee;border-radius:3px;padding:2px 5px;min-width:30px;">
                        <div style="font-size:.42rem;color:#888;text-transform:uppercase;letter-spacing:.3px;">1</div>
                        <div style="font-family:'Bitter',serif;font-size:.68rem;font-weight:600;color:#333;">{rh}</div>
                    </div>
                    <div style="text-align:center;background:#e8e8ee;border-radius:3px;padding:2px 5px;min-width:30px;">
                        <div style="font-size:.42rem;color:#888;text-transform:uppercase;letter-spacing:.3px;">X</div>
                        <div style="font-family:'Bitter',serif;font-size:.68rem;font-weight:600;color:#333;">{rx}</div>
                    </div>
                    <div style="text-align:center;background:#e8e8ee;border-radius:3px;padding:2px 5px;min-width:30px;">
                        <div style="font-size:.42rem;color:#888;text-transform:uppercase;letter-spacing:.3px;">2</div>
                        <div style="font-family:'Bitter',serif;font-size:.68rem;font-weight:600;color:#333;">{ra}</div>
                    </div>
                </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:110px;">
                {abadge}
                <span style="font-size:.75rem;font-weight:700;color:#555570;letter-spacing:.8px;text-transform:uppercase;">{away}</span>
            </div>
        </div>
    </div>
    <div style="height:1px;background:#e0e0e8;margin:0 0 12px;"></div>
    """, unsafe_allow_html=True)

    # ── STATS + LINEUPS side by side ──────────────────────────────────────────
    stat_sections = [
        ("Shots",           hs,  a_s),
        ("Shots on Target", hst, ast),
        ("Corners",         hc,  ac),
        ("Yellow Cards",    hy,  ay),
        ("Red Cards",       hr,  ar),
    ]

    def stat_html(label, hv, av):
        return (
            '<div style="display:flex;align-items:center;justify-content:center;gap:16px;margin-bottom:9px;">'
            f'<div style="font-family:\'Bitter\',serif;font-size:1.05rem;font-weight:700;color:#e0e0e0;width:36px;text-align:right;">{hv}</div>'
            f'<div style="font-size:.62rem;color:#444466;text-transform:uppercase;letter-spacing:.8px;width:110px;text-align:center;">{label}</div>'
            f'<div style="font-family:\'Bitter\',serif;font-size:1.05rem;font-weight:700;color:#e0e0e0;width:36px;text-align:left;">{av}</div>'
            '</div>'
        )

    # Position sort order
    POS_ORDER = {"Goalkeeper":0,"Right Back":1,"Right Centre Back":1,"Centre Back":1,
                 "Left Centre Back":1,"Left Back":1,"Right Wing Back":2,"Left Wing Back":2,
                 "Right Defensive Midfield":3,"Centre Defensive Midfield":3,"Left Defensive Midfield":3,
                 "Right Centre Midfield":4,"Centre Midfield":4,"Left Centre Midfield":4,
                 "Right Midfield":4,"Left Midfield":4,"Right Attacking Midfield":5,
                 "Centre Attacking Midfield":5,"Left Attacking Midfield":5,
                 "Right Wing":6,"Left Wing":6,"Centre Forward":7,"Right Centre Forward":7,"Left Centre Forward":7}

    def sort_players(player_list):
        starters  = [p for p in player_list if p.get("minutes",0) >= 45]
        subs      = [p for p in player_list if p.get("minutes",0) < 45]
        starters.sort(key=lambda p: POS_ORDER.get(p.get("position",""),99))
        subs.sort(key=lambda p: -p.get("minutes",0))
        return starters, subs

    def player_row_html(p, side):
        name   = p["name"]
        mins   = p["minutes"]
        xg_val = p["xg"]
        gs     = p.get("goals", 0)
        is_red = name in reds_by_player
        icons  = ("⚽" * gs) + ("🟥" if is_red else "")
        bold   = "font-weight:600;" if (gs or is_red) else ""
        xg_str  = f"{xg_val:.2f}" if xg_val > 0 else "—"
        mins_str = f"{mins}'"
        return (
            f'<div style="display:flex;align-items:center;padding:0;line-height:1.55;font-size:.72rem;">'
            f'<span style="color:#444;{bold}flex:1;overflow:hidden;white-space:nowrap;'
            f'text-overflow:ellipsis;padding-right:4px;">{name}{(" "+icons) if icons else ""}</span>'
            f'<span style="color:#888;font-size:.62rem;width:22px;text-align:right;flex-shrink:0;">{mins_str}</span>'
            f'<span style="color:#aaa;font-size:.62rem;width:26px;text-align:right;flex-shrink:0;">{xg_str}</span>'
            f'</div>'
        )

    def team_col_html(team_name, player_list, label_side="left"):
        starters, subs = sort_players(player_list)
        sep = '<div style="height:1px;background:#e0e0e8;margin:3px 0 2px;"></div>'
        header = (
            f'<div style="display:flex;align-items:center;padding:0 0 3px;'
            f'border-bottom:1px solid #ddd;margin-bottom:2px;">'
            f'<span style="font-size:.58rem;font-weight:700;color:#333;text-transform:uppercase;'
            f'letter-spacing:.5px;flex:1;">{team_name}</span>'
            f'<span style="font-size:.5rem;color:#aaa;width:22px;text-align:right;flex-shrink:0;">min</span>'
            f'<span style="font-size:.5rem;color:#aaa;width:26px;text-align:right;flex-shrink:0;">xg</span>'
            f'</div>'
        )
        rows = "".join(player_row_html(p, label_side) for p in starters)
        if subs:
            rows += sep + "".join(player_row_html(p, label_side) for p in subs)
        return header + rows

    home_players = players.get(home, [])
    away_players = players.get(away, [])

    # One placeholder controls the full content area
    main_ph = st.empty()

    def make_pitch(shot, idx, total):
        is_home   = shot["team_fd"] == shot["home_fd"]
        rx, ry    = shot["x"], shot["y"]
        is_goal   = shot["is_goal"] == 1
        xg        = shot["xg"]
        player    = shot["player"]
        minute    = shot["minute"]
        score     = shot["score_after"]
        outcome   = shot["outcome"]
        team      = shot["team_fd"]
        opp       = shot["away_fd"] if is_home else shot["home_fd"]

        # StatsBomb ALWAYS stores x from shooting team perspective:
        # x=120=opponent goal, x=60=halfway. No home/away flip needed.
        nx = max(4, min(556, (rx - 60) / 60 * 560))
        ny = max(4, min(316, ry / 80 * 320))

        # Dot: size scales with xG, colour by outcome
        dot_r  = max(8, min(20, int(xg * 65)))
        if is_goal:
            dot_fill   = "#ffffff"
            dot_stroke = "#e32221"
            dot_sw     = 3.5
            ring_r     = dot_r + 7
            pulse_ring = (f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{ring_r}" '
                          f'fill="none" stroke="rgba(227,34,33,0.35)" stroke-width="2"/>')
        else:
            dot_fill   = "#8888bb"
            dot_stroke = "rgba(160,160,200,0.7)"
            dot_sw     = 1.5
            pulse_ring = ""

        # xG bar width (0-100 out of max 140px)
        xg_bar_w = min(140, int(xg * 140 / 0.5))   # 0.5 xg = full bar

        # Top info card colours
        if is_goal:
            card_bg    = "#1a0505"
            card_border= "#e32221"
            score_col  = "#e32221"
            tag_html   = ('<span style="background:#e32221;color:#fff;font-size:.75rem;'
                           'font-weight:800;padding:3px 12px;border-radius:4px;'
                           'text-transform:uppercase;letter-spacing:1.5px;'
                           'box-shadow:0 2px 8px rgba(227,34,33,0.5);">GOAL</span>')
        else:
            card_bg    = "#0e0e1a"
            card_border= "#2a2a45"
            score_col  = "#888"
            shot_lbl   = outcome if outcome not in ("nan","") else "Shot"
            tag_html   = (f'<span style="color:#555577;font-size:.62rem;'
                           f'font-weight:500;letter-spacing:.5px;">{shot_lbl}</span>')

        highlight_label = f"Highlight {idx+1} / {total}"

        # Shorten player name if too long
        pname = player if len(player) <= 30 else player[:28] + "…"

        return (
            # Outer wrapper — dark card, no scroll
            '<div style="display:flex;justify-content:center;padding:6px 0;">'
            '<div style="width:560px;border-radius:12px;overflow:hidden;'
            f'border:1px solid {card_border};box-shadow:0 4px 24px rgba(0,0,0,0.4);">'

            # ── TOP INFO CARD ──────────────────────────────────────────────
            f'<div style="background:{card_bg};padding:14px 18px 10px;">'

            # Row 1: player name left, counter right
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="font-family:Bitter,serif;font-size:1.1rem;font-weight:800;color:#f0f0f0;letter-spacing:.5px;">{pname}</span>'
            f'<span style="font-size:.65rem;font-weight:700;color:#8888bb;letter-spacing:.8px;text-transform:uppercase;">{highlight_label}</span>'
            '</div>'

            # Row 2: outcome tag, shooting team, minute
            '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">' +
            tag_html +
            f'<span style="font-size:.72rem;color:#9090b8;font-weight:600;">{team}</span>'
            f'<span style="font-size:.72rem;color:#555577;">{minute}\'</span>'
            '</div>'

            # Row 3: xG value + bar
            '<div style="display:flex;align-items:center;gap:10px;margin-top:8px;">'
            '<span style="font-size:.6rem;color:#8888bb;text-transform:uppercase;font-weight:700;letter-spacing:.7px;width:18px;">xG</span>'
            f'<span style="font-family:Bitter,serif;font-size:1.3rem;font-weight:800;color:#f0f0f0;">{xg:.2f}</span>'
            # xG bar
            '<div style="flex:1;height:4px;background:#1e1e35;border-radius:2px;overflow:hidden;">'
            f'<div style="width:{xg_bar_w}px;height:4px;background:linear-gradient(90deg,#5555aa,#9999dd);border-radius:2px;"></div>'
            '</div>'
            # score badge
            f'<span style="font-family:Bitter,serif;font-size:.8rem;font-weight:700;color:{score_col};'
            f'background:#0a0a18;border:1px solid #1e1e38;border-radius:4px;padding:2px 8px;">'
            + (f'Score: {score}' if is_goal else '&nbsp;') +
            '</span>'
            '</div>'
            '</div>'   # end info card

            # ── PITCH ──────────────────────────────────────────────────────
            f'<svg width="560" height="320" viewBox="0 0 560 320" xmlns="http://www.w3.org/2000/svg">'
            # Pitch gradient background
            '<defs>'
            '<linearGradient id="pitchGrad" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0%" stop-color="#1e5c28"/>'
            '<stop offset="100%" stop-color="#2d7a3a"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="560" height="320" fill="url(#pitchGrad)"/>'
            # Pitch stripes (subtle)
            + "".join(
                f'<rect x="{i*40}" y="0" width="20" height="320" fill="rgba(0,0,0,0.04)"/>'
                for i in range(14)
            ) +
            # Touchlines
            '<rect x="1" y="1" width="558" height="318" fill="none" stroke="rgba(255,255,255,0.45)" stroke-width="1.5"/>'
            # Halfway line (left edge)
            '<line x1="0" y1="0" x2="0" y2="320" stroke="rgba(255,255,255,0.3)" stroke-width="1.5"/>'
            # Penalty area: 378-560 x, 97-271 y (proportional)
            '<rect x="406" y="79" width="154" height="162" fill="rgba(0,0,0,0.12)" stroke="rgba(255,255,255,0.5)" stroke-width="1.5"/>'
            # Six-yard box
            '<rect x="504" y="117" width="56" height="86" fill="rgba(0,0,0,0.08)" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>'
            # Goal
            '<rect x="555" y="140" width="8" height="60" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.8)" stroke-width="2"/>'
            # Goal line endpoints (dots)
            '<circle cx="555" cy="144" r="2" fill="rgba(255,255,255,0.6)"/>'
            '<circle cx="555" cy="208" r="2" fill="rgba(255,255,255,0.6)"/>'
            # Penalty spot
            '<circle cx="457" cy="160" r="2.5" fill="rgba(255,255,255,0.6)"/>'
            # Penalty arc outside the box
            '<path d="M 406 92 A 85 85 0 0 0 406 228" fill="none" stroke="rgba(255,255,255,0.45)" stroke-width="1.5"/>'
            # Penalty arc — curves OUTSIDE the box (away from goal)
            # Penalty arc — outside the box
            # Shot dot pulse ring (goals only)
            + pulse_ring +
            # Shot dot
            f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{dot_r}" fill="{dot_fill}" fill-opacity="0.9" stroke="{dot_stroke}" stroke-width="{dot_sw}"/>'
            # Crosshair lines to goal (subtle, goals only)
            + (f'<line x1="{nx:.1f}" y1="{ny:.1f}" x2="555" y2="144" stroke="rgba(227,34,33,0.12)" stroke-width="1" stroke-dasharray="4,4"/>'
               f'<line x1="{nx:.1f}" y1="{ny:.1f}" x2="555" y2="208" stroke="rgba(227,34,33,0.12)" stroke-width="1" stroke-dasharray="4,4"/>'
               if is_goal else "") +
            '</svg>'

            '</div></div>'   # end card + wrapper
        )



    def make_red_card(rc, idx, total):
        player   = rc["player"]
        team     = rc["team_fd"]
        minute   = rc["minute"]
        score    = rc.get("score_at", "—")
        pname    = player if len(player) <= 30 else player[:28] + "…"
        highlight = f"Highlight {idx+1} / {total}"
        min_str  = str(minute) + chr(39)

        card_html = (
            '<div style="display:flex;justify-content:center;padding:6px 0;">'
            '<div style="width:560px;border-radius:12px;overflow:hidden;'
            'border:1px solid #c0000a;box-shadow:0 4px 32px rgba(192,0,10,0.35);">'

            # Header
            '<div style="background:#0d0005;padding:14px 20px 10px;">'
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">'
            '<span style="font-size:.6rem;font-weight:700;color:#c0000a;text-transform:uppercase;letter-spacing:1.2px;">Red Card</span>'
            + f'<span style="font-size:.65rem;font-weight:700;color:#8888bb;letter-spacing:.8px;text-transform:uppercase;">{highlight}</span>'
            + '</div>'
            + f'<div style="font-family:Bitter,serif;font-size:1.6rem;font-weight:800;color:#f0f0f0;letter-spacing:.5px;margin-bottom:4px;">{pname}</div>'
            + f'<div style="font-size:.78rem;color:#8888aa;margin-bottom:10px;">'
            + f'<span style="color:#c8c8e0;font-weight:600;">{team}</span></div>'
            + '</div>'

            # Visual block
            + '<div style="background:linear-gradient(135deg,#1a0003,#2d0008,#1a0003);'
            'padding:28px 20px;display:flex;align-items:center;justify-content:center;gap:36px;'
            'border-top:1px solid #2d0008;border-bottom:1px solid #2d0008;">'

            # Red card rectangle
            + '<div style="width:72px;height:100px;background:linear-gradient(145deg,#e8000a,#9a0007);'
            'border-radius:8px;box-shadow:0 6px 28px rgba(200,0,10,0.7),0 0 0 1px rgba(255,80,80,0.25);'
            'position:relative;overflow:hidden;">'
            '<div style="position:absolute;top:0;left:0;right:0;height:42%;'
            'background:linear-gradient(180deg,rgba(255,255,255,0.2),transparent);'
            'border-radius:8px 8px 0 0;"></div></div>'

            # Info panel
            + '<div style="display:flex;flex-direction:column;gap:14px;">'
            + f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;">'
            + f'<div style="font-size:.52rem;color:#4a4a6a;text-transform:uppercase;letter-spacing:.8px;">Score at time</div>'
            + f'<div style="font-family:Bitter,serif;font-size:1.9rem;font-weight:800;color:#f0f0f0;letter-spacing:3px;text-align:center;">{score}</div>'
            + f'<div style="display:inline-block;background:#c0000a;color:#fff;font-family:Bitter,serif;'
            + f'font-size:1rem;font-weight:700;padding:3px 14px;border-radius:20px;text-align:center;">{min_str}</div>'
            + '</div></div>'

            + '</div></div>'
        )
        return card_html

    def static_summary_html():
        def all_stats():
            return "".join(
                '<div style="display:flex;align-items:center;justify-content:center;gap:16px;margin-bottom:9px;">'
                f'<div style="font-family:Bitter,serif;font-size:1.05rem;font-weight:700;color:#222;width:36px;text-align:right;">{hv}</div>'
                f'<div style="font-size:.62rem;color:#888;text-transform:uppercase;letter-spacing:.8px;width:110px;text-align:center;">{lbl}</div>'
                f'<div style="font-family:Bitter,serif;font-size:1.05rem;font-weight:700;color:#222;width:36px;text-align:left;">{av}</div>'
                '</div>'
                for lbl, hv, av in stat_sections
            )
        def plist_html(team_name, plist):
            starters, subs = sort_players(plist)
            def prow(p):
                n=p["name"]; gs=p.get("goals",0); ir=n in reds_by_player
                icons=("\u26bd"*gs)+("\U0001f7e5" if ir else "")
                bl="font-weight:600;" if (gs or ir) else ""
                xs="{:.2f}".format(p["xg"]) if p["xg"]>0 else "\u2014"
                ms=str(p["minutes"])+"'"
                icon_str=(" "+icons) if icons else ""
                return ("<div style='display:flex;align-items:center;line-height:1.5;font-size:.7rem;'>"
                        "<span style='color:#333;"+bl+"flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;'>"+n+icon_str+"</span>"
                        "<span style='color:#888;font-size:.6rem;width:22px;text-align:right;'>"+ms+"</span>"
                        "<span style='color:#aaa;font-size:.6rem;width:26px;text-align:right;'>"+xs+"</span>"
                        "</div>")
            sep='<div style="height:1px;background:#e0e0e8;margin:3px 0;"></div>'
            hdr=(f'<div style="display:flex;border-bottom:1px solid #ddd;padding-bottom:3px;margin-bottom:2px;">'
                 f'<span style="font-size:.58rem;font-weight:700;color:#333;text-transform:uppercase;letter-spacing:.5px;flex:1;">{team_name}</span>'
                 '<span style="font-size:.5rem;color:#aaa;width:22px;text-align:right;">min</span>'
                 '<span style="font-size:.5rem;color:#aaa;width:26px;text-align:right;">xg</span></div>')
            rows="".join(prow(p) for p in starters)
            if subs: rows+=sep+"".join(prow(p) for p in subs)
            return f'<div>{hdr}{rows}</div>'
        return (
            '<div style="height:1px;background:#e0e0e8;margin:6px 0 10px;"></div>'
            '<div style="display:flex;gap:8px;">'
            f'<div style="flex:1.3;">{plist_html(home, home_players)}</div>'
            f'<div style="flex:0.9;padding-top:4px;">{all_stats()}</div>'
            f'<div style="flex:1.3;">{plist_html(away, away_players)}</div>'
            '</div>'
        )

    # ── PHASE 1: animated stats reveal + players ──────────────────────────────
    # Calculate stats animation speed to match intro audio length
    _intro_dur = get_audio_duration(home, away, "intro", -1, fallback=2.8) if has_audio(home, away, "intro", -1) else 2.8
    _stat_step_sleep = max(0.008, _intro_dur / (5 * 40))  # fill intro duration
    with main_ph.container():
        # Embed intro audio inline so it stops when main_ph is replaced
        if has_audio(home, away, "intro", -1):
            from voice_loader import get_audio_b64
            b64_intro = get_audio_b64(home, away, "intro", -1)
            if b64_intro:
                st.markdown(
                    f'<audio autoplay style="display:none;"><source src="data:audio/mp3;base64,{b64_intro}" type="audio/mp3"></audio>',
                    unsafe_allow_html=True
                )
        col_home, col_stats, col_away = st.columns([1.3, 0.8, 1.3])
        with col_home:
            st.markdown(team_col_html(home, home_players, "left") if has_sb
                        else '<div style="color:#aaa;font-size:.7rem;text-align:center;">—</div>',
                        unsafe_allow_html=True)
        with col_stats:
            phs = [st.empty() for _ in stat_sections]
            pp = st.empty()
            for idx, (label, hv, av) in enumerate(stat_sections):
                pb = pp.progress(0, text=f"  {label}")
                for s in range(40):
                    time.sleep(_stat_step_sleep)
                    pb.progress(int((s+1)*100/40), text=f"  {label}")
                pp.empty()
                phs[idx].markdown(stat_html(label, hv, av), unsafe_allow_html=True)
        with col_away:
            st.markdown(team_col_html(away, away_players, "right") if has_sb
                        else '<div style="color:#aaa;font-size:.7rem;text-align:center;">—</div>',
                        unsafe_allow_html=True)
        if not has_sb:
            st.markdown('<div style="text-align:center;color:#aaa;font-size:.65rem;margin-top:6px;">'
                        'Player data: Last 10 Leverkusen matches only (MD25-34)</div>', unsafe_allow_html=True)

    if not (has_sb and combined_seq):
        return

    time.sleep(2.0)  # 2 second buffer after intro + stats finish

    # ── PHASE 2: highlights — shots + red cards, sorted by minute ─────────────
    BLANK = '<div style="height:120px;background:#f5f5f8;border-radius:8px;margin:8px auto;width:560px;"></div>'
    total = len(combined_seq)
    for i, item in enumerate(combined_seq):
        if i > 0:
            main_ph.markdown(BLANK, unsafe_allow_html=True)
            time.sleep(0.3)
        # Build card HTML + embed audio inline so it stops when card is replaced
        audio_html = ""
        if has_audio(home, away, "highlight", i):
            from voice_loader import get_audio_b64
            b64 = get_audio_b64(home, away, "highlight", i)
            if b64:
                audio_html = f'<audio autoplay style="display:none;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        if item["type"] == "red_card":
            main_ph.markdown(make_red_card(item, i, total) + audio_html, unsafe_allow_html=True)
        else:
            main_ph.markdown(make_pitch(item, i, total) + audio_html, unsafe_allow_html=True)
        hl_wait = get_audio_duration(home, away, "highlight", i, fallback=5.0) + 0.3
        time.sleep(hl_wait)

    # Chatbot removed — use tabs for stats instead

    # ── PHASE 3: static summary — all at once ─────────────────────────────────
    main_ph.markdown(static_summary_html(), unsafe_allow_html=True)


# ── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_league_tables():
    try:
        with open("statsbomb_cache/league_tables.json") as f:
            return json.load(f)
    except Exception:
        return {}

@st.cache_data
def load_top_scorers():
    try:
        with open("statsbomb_cache/top_scorers.json") as f:
            return json.load(f)
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def cached_load():
    return load_data()

@st.cache_data(ttl=86400)
def _cached_xg():
    """Module-level cache so Streamlit actually persists it across reruns."""
    return build_xg_lookup()


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    if "page" not in st.session_state:
        st.session_state.page = "matches"


    # German flag SVG - three horizontal bands: black, red, gold
    header_badge = (
        '<svg width="42" height="28" viewBox="0 0 42 28" xmlns="http://www.w3.org/2000/svg" '
        'style="flex-shrink:0;border-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,0.5);">'
        '<rect width="42" height="9.33" y="0" fill="#000000"/>'
        '<rect width="42" height="9.33" y="9.33" fill="#dd0000"/>'
        '<rect width="42" height="9.34" y="18.66" fill="#ffce00"/>'
        '</svg>'
    )
    # Header + About button side by side
    st.markdown(f'''
    <div class="dash-header">
        {header_badge}
        <h1>Bundesliga 2023 / 24</h1>
    </div>''', unsafe_allow_html=True)

    st.markdown('''<style>
    /* Style the About/Back nav button — targets by position (first button rendered) */
    [data-testid="stMainBlockContainer"] > div > div > div > div:nth-child(2) button {
        background: transparent !important;
        border: 1.5px solid #ffc800 !important;
        color: #ffc800 !important;
        font-weight: 700 !important;
        letter-spacing: 1.2px !important;
        border-radius: 20px !important;
        font-size: .72rem !important;
        box-shadow: 0 0 16px rgba(255,200,0,.25) !important;
        text-transform: uppercase !important;
        padding: 4px 18px !important;
    }
    [data-testid="stMainBlockContainer"] > div > div > div > div:nth-child(2) button:hover {
        background: rgba(255,200,0,.15) !important;
        color: #fff !important;
        border-color: #fff !important;
        box-shadow: 0 0 22px rgba(255,200,0,.45) !important;
    }
    </style>''', unsafe_allow_html=True)

        # Use columns to position button on the right
    _, right_col = st.columns([9, 1.4])
    with right_col:
        is_about = st.session_state.page == "about"
        btn_label = "← Back" if is_about else "About"
        if st.button(btn_label, key="nav_btn"):
            st.session_state.page = "about" if not is_about else "matches"
            st.session_state["stop_audio"] = True
            st.rerun()

    if st.session_state.get("stop_audio"):
        import streamlit.components.v1 as _stc
        _stc.html("""<script>
        var audios = window.parent.document.querySelectorAll("audio");
        for(var i=0;i<audios.length;i++){
            audios[i].pause();
            audios[i].currentTime=0;
            audios[i].src="";
        }
        </script>""", height=0)
        st.session_state["stop_audio"] = False

    if st.session_state.page == "about":
        show_about()
        return

    # Load pre-calculated tables
    all_league_tables = load_league_tables()
    all_top_scorers   = load_top_scorers()

    with st.spinner(""):
        try:
            df = cached_load()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            return

    rounds    = get_available_rounds(df)
    max_round = max(rounds)

    xg_lookup = _cached_xg()

    # ── View selector tabs ────────────────────────────────────────────────────
    if "view_tab" not in st.session_state:
        st.session_state.view_tab = "results"

    st.markdown("""<style>
    div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button {
        background: #080810 !important; border: 1.5px solid #ffc800 !important;
        color: #ffc800 !important; font-size: .62rem !important;
        font-weight: 700 !important; letter-spacing: .8px !important;
        padding: 4px 8px !important; border-radius: 20px !important;
        height: auto !important; min-height: 0 !important;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button[kind="primary"] {
        background: #d20515 !important; border-color: #d20515 !important;
        color: #fff !important; box-shadow: 0 0 10px rgba(210,5,21,.3) !important;
    }
    </style>""", unsafe_allow_html=True)

    _, col_r, col_l, col_s, _ = st.columns([1.5, 2, 2, 2, 1.5])
    with col_r:
        if st.button("📅  Results", key="tab_results",
                     type="primary" if st.session_state.view_tab=="results" else "secondary",
                     use_container_width=True):
            st.session_state.view_tab = "results"
            st.session_state["stop_audio"] = True
            st.session_state["open_match"] = None; st.rerun()
    with col_l:
        if st.button("🏆  League Table", key="tab_league",
                     type="primary" if st.session_state.view_tab=="league" else "secondary",
                     use_container_width=True):
            st.session_state.view_tab = "league"
            st.session_state["stop_audio"] = True
            st.session_state["open_match"] = None; st.rerun()
    with col_s:
        if st.button("⚽  Top Scorers", key="tab_scorers",
                     type="primary" if st.session_state.view_tab=="scorers" else "secondary",
                     use_container_width=True):
            st.session_state.view_tab = "scorers"
            st.session_state["stop_audio"] = True
            st.session_state["open_match"] = None; st.rerun()

    _l, sel_col, badge_col, _r = st.columns([3, 3, 1, 3])

    with sel_col:
        rounds_desc = sorted(rounds, reverse=True)  # 34,33,32...
        # Preserve selected matchday across tab switches
        if "selected_md" not in st.session_state:
            st.session_state.selected_md = rounds_desc[0]
        if st.session_state.selected_md not in rounds_desc:
            st.session_state.selected_md = rounds_desc[0]
        selected = st.selectbox(
            "Matchday",
            options=rounds_desc,
            index=rounds_desc.index(st.session_state.selected_md),
            format_func=lambda r: f"Matchday {r}",
            label_visibility="collapsed",
            key="md_selector",
        )
        if st.session_state.get("_prev_md") != selected:
            st.session_state["stop_audio"] = True
            st.session_state["open_match"] = None  # clear any open dialog
        st.session_state["_prev_md"] = selected
        st.session_state.selected_md = selected

    with badge_col:
        st.markdown(f"""
        <div style="padding-top:6px;">
            <span class="round-badge">MD {selected}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    LEV_STATS_FROM_ROUND = 25   # Stats+ (xG + players) only from this round onwards
    round_df = df.filter(pl.col("Round") == selected)

    # ── LEAGUE TABLE VIEW ─────────────────────────────────────────────────────
    if st.session_state.view_tab == "league":
        md_key = str(selected)
        table_rows = all_league_tables.get(md_key, [])
        st.markdown(f'<p style="color:#555570;font-size:.75rem;text-align:center;margin-bottom:8px;">'  
                    f'Bundesliga table after Matchday {selected}</p>', unsafe_allow_html=True)
        if not table_rows:
            st.info("Run build_tables.py to generate league tables.")
        else:
            html = '<table class="league-table" style="width:75%;margin:0 auto;"><thead><tr>'
            html += '<th style="width:28px"></th><th style="text-align:left">Club</th>'
            html += '<th>P</th><th>W</th><th>D</th><th>L</th>'
            html += '<th>GF</th><th>GA</th><th>GD</th><th>Pts</th></tr></thead><tbody>'
            for i, r in enumerate(table_rows, 1):
                is_lev = "Leverkusen" in r["team"]
                row_cls = "lev-row" if is_lev else ""
                gd = r["gd"]
                gd_cls = "gd-pos" if gd > 0 else "gd-neg" if gd < 0 else ""
                gd_str = f"+{gd}" if gd > 0 else str(gd)
                badge = badge_svg(r["team"], 18)
                html += f'<tr class="{row_cls}">'
                html += f'<td class="pos-num">{i}</td>'
                html += f'<td>{badge} {r["team"]}</td>'
                html += f'<td>{r["played"]}</td>'
                html += f'<td>{r["won"]}</td><td>{r["drawn"]}</td><td>{r["lost"]}</td>'
                html += f'<td>{r["gf"]}</td><td>{r["ga"]}</td>'
                html += f'<td class="{gd_cls}">{gd_str}</td>'
                html += f'<td class="pts-cell">{r["pts"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        return

    # ── TOP SCORERS VIEW ──────────────────────────────────────────────────────
    if st.session_state.view_tab == "scorers":
        md_key = str(selected)
        scorer_rows = all_top_scorers.get(md_key, [])
        st.markdown(f'<p style="color:#555570;font-size:.75rem;text-align:center;margin-bottom:8px;">'
                    f'Top scorers after Matchday {selected}</p>', unsafe_allow_html=True)
        if not scorer_rows:
            st.info("Run build_tables.py to generate top scorer tables.")
        else:
            html = '<table class="scorer-table" style="width:55%;margin:0 auto;"><thead><tr>'
            html += '<th>#</th><th style="text-align:left">Player</th>'
            html += '<th style="text-align:left">Club</th>'
            html += '<th style="text-align:right;padding-right:12px">Goals</th></tr></thead><tbody>'
            for s in scorer_rows:
                is_lev = "Leverkusen" in s.get("team","")
                row_cls = "scorer-lev" if is_lev else ""
                badge = badge_svg(s.get("team",""), 16)
                html += f'<tr class="{row_cls}">'
                html += f'<td>{s["rank"]}</td>'
                html += f'<td>{s["name"]}</td>'
                html += f'<td>{badge} {s.get("team","")}</td>'
                html += f'<td class="scorer-goals">{s["goals"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        return


    if "open_match" not in st.session_state:
        st.session_state.open_match = None

    for row in round_df.iter_rows(named=True):
        home = row["HomeTeam"];  away = row["AwayTeam"]
        home = row["HomeTeam"];  away = row["AwayTeam"]
        dialog_key = f"{home}_{away}_{int(time.time()*100)%100000}"
        fthg = si(row["FTHG"]); ftag = si(row["FTAG"])
        date = str(row["Date"]) if row["Date"] else "—"
        res  = result_of(fthg, ftag)
        hb = badge_svg(home, 22)
        ab = badge_svg(away, 22)
        is_lev_stats = ("Leverkusen" in (home, away)) and (row["Round"] >= LEV_STATS_FROM_ROUND)
        hxg, axg = get_match_xg(xg_lookup, home, away) if is_lev_stats else (None, None)

        _l2, row_col, btn_col, _r2 = st.columns([2, 5, 0.6, 2.4])

        if is_lev_stats and hxg is not None and axg is not None:
            xg_html = f'<div class="xg-wrap"><div class="xg-values"><span>{hxg:.2f}</span><span class="xg-label">&nbsp;XG&nbsp;</span><span>{axg:.2f}</span></div></div>'
        else:
            xg_html = '<div class="xg-wrap"></div>'

        with row_col:
            st.markdown(f"""
            <div class="mrow">
                <div class="mdate">{date}</div>
                {hb}
                <div class="mteam">{home}</div>
                <div class="mscore-wrap">
                    <div class="mscore">{fthg} – {ftag}</div>
                    {xg_html}
                </div>
                <div class="mteam">{away}</div>
                {ab}
            </div>""", unsafe_allow_html=True)

        btn_label = "Stats +" if is_lev_stats else "Stats"
        with btn_col:
            if st.button(btn_label, key=f"btn_{home}_{away}"):
                st.session_state.open_match = row

    if st.session_state.open_match is not None:
        show_match_dialog(st.session_state.open_match)
        st.session_state.open_match = None

    _, foot_col, _ = st.columns([2, 5, 2])
    with foot_col:
        st.markdown("""
        <div style="text-align:center;color:#111128;font-size:.62rem;
                    margin-top:28px;padding-top:10px;
                    border-top:1px solid #0e0e1c;letter-spacing:.5px;">
            BUNDESLIGA 2023/24 · PHASE 2
        </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
