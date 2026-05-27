"""
player_nationalities.py
=======================
Maps Leverkusen players to their nationality and the goal celebration
language/phrase to use when they score.

Goal words by language (for Eleven v3 multilingual celebrations):
  German:     TOOOOOR!          (Tor = goal, also means gate)
  Spanish:    GOLAZO!           (augmentative — a great goal)
  Portuguese: GOL! Que golaço!  (Brazilian football roots)
  French:     BUT!              (sharp, elegant)
  Italian:    Gol spettacolare! (spectacular goal)
  Nigerian:   GOAL-O! Oya!      (Nigerian Pidgin exclamation)
  Swiss:      TOR! Wunderbar!   (Swiss German)
  Croatian:   GOL!              (same as Spanish/Italian)
  Slovak:     GÓL!              (with accent)
  Ghanaian:   GOAL! Ayeee!      (Ghanaian exclamation of joy)
  Nigerian Yoruba: Góóólu!

Audio tag to use with v3 for the multilingual burst:
  Always: [SHOUTING] before the goal word
  Then:   [crowd cheering] after
  Then:   [warmly] for the reflection line
"""

PLAYER_NATIONALITIES = {
    # German players — TOOOOOR!
    "Florian Wirtz":              {"nat": "German",     "goal_cry": "TOOOOOR!",           "lang": "German",     "flag": "🇩🇪"},
    "Jonathan Tah":               {"nat": "German",     "goal_cry": "TOOOOOR!",           "lang": "German",     "flag": "🇩🇪"},
    "Jonas Hofmann":              {"nat": "German",     "goal_cry": "TOOOOOR!",           "lang": "German",     "flag": "🇩🇪"},
    "Robert Andrich":             {"nat": "German",     "goal_cry": "TOOOOOR!",           "lang": "German",     "flag": "🇩🇪"},

    # Nigerian — Goal-O! Oya!
    "Victor Okoh Boniface":       {"nat": "Nigerian",   "goal_cry": "GOAL-O! Oya!",       "lang": "Nigerian",   "flag": "🇳🇬"},
    "Victor Boniface":            {"nat": "Nigerian",   "goal_cry": "GOAL-O! Oya!",       "lang": "Nigerian",   "flag": "🇳🇬"},

    # Spanish — GOLAZO!
    "Alejandro Grimaldo Garcia":  {"nat": "Spanish",    "goal_cry": "GOLAZO!",            "lang": "Spanish",    "flag": "🇪🇸"},
    "Alex Grimaldo":              {"nat": "Spanish",    "goal_cry": "GOLAZO!",            "lang": "Spanish",    "flag": "🇪🇸"},

    # Dutch — DOELPUNT!
    "Jeremie Frimpong":           {"nat": "Dutch",      "goal_cry": "DOELPUNT!",          "lang": "Dutch",      "flag": "🇳🇱"},

    # Czech — GÓL!
    "Patrik Schick":              {"nat": "Czech",      "goal_cry": "GÓL! Neuvěřitelné!", "lang": "Czech",      "flag": "🇨🇿"},
    "Adam Hlozek":                {"nat": "Czech",      "goal_cry": "GÓL!",               "lang": "Czech",      "flag": "🇨🇿"},

    # Swiss — TOR! Wunderbar!
    "Granit Xhaka":               {"nat": "Swiss",      "goal_cry": "TOR! Wunderbar!",    "lang": "Swiss",      "flag": "🇨🇭"},

    # Ghanaian — GOAL! Ayeee!
    "Odilon Kossonou":            {"nat": "Ivorian",    "goal_cry": "BUUUT!",             "lang": "French",     "flag": "🇨🇮"},

    # Croatian — GOL!
    "Josip Stanisic":             {"nat": "Croatian",   "goal_cry": "GOL! Fenomenalno!",  "lang": "Croatian",   "flag": "🇭🇷"},

    # French (Algerian heritage) — BUT!
    "Amine Adli":                 {"nat": "French",     "goal_cry": "BUUUT!",             "lang": "French",     "flag": "🇫🇷"},
    "Nathan Tella":               {"nat": "French",     "goal_cry": "BUUUT!",             "lang": "French",     "flag": "🇫🇷"},

    # Argentine — GOLAZO!
    "Exequiel Alejandro Palacios":{"nat": "Argentine",  "goal_cry": "GOLAZO!",            "lang": "Spanish",    "flag": "🇦🇷"},

    # Ecuadorian — GOOOOL!
    "Piero Martin Hincapie Reyna":{"nat": "Ecuadorian", "goal_cry": "GOOOOOL!",           "lang": "Spanish",    "flag": "🇪🇨"},
}

def get_goal_cry(player_name):
    """Return (goal_cry, language, flag) for a player, defaulting to English."""
    # Direct match
    if player_name in PLAYER_NATIONALITIES:
        p = PLAYER_NATIONALITIES[player_name]
        return p["goal_cry"], p["lang"], p["flag"]
    # Partial match
    for k, p in PLAYER_NATIONALITIES.items():
        if player_name.lower() in k.lower() or k.lower() in player_name.lower():
            return p["goal_cry"], p["lang"], p["flag"]
    return "GOAAAAAL!", "English", "🌍"


# Eleven v3 audio tags for football commentary
# Use these in generated text before sending to ElevenLabs
AUDIO_TAGS = {
    "pre_goal_build":    "[calm, building]",
    "approaching_goal":  "[EXCITED]",
    "goal_shout":        "[SHOUTING]",
    "crowd":             "[crowd cheering]",
    "silence":           "[pause]",
    "warmth":            "[warmly]",
    "reverence":         "[quietly]",
    "sad":               "[sorrowful]",
    "gasp":              "[gasps]",
    "laugh_joy":         "[laughs]",
}

# BayArena atmosphere sounds available in Eleven v3
STADIUM_SOUNDS = {
    "goal_crowd":    "[crowd cheering]",    # crowd erupting after goal
    "tense_crowd":   "[crowd noise]",       # building tension
    "whistle":       "[whistle]",           # referee whistle
    "gasp":          "[crowd gasps]",       # near miss or red card
}

# Leverkusen cultural phrases to weave into commentary
LEVERKUSEN_PHRASES = {
    "team_name":    "Die Werkself",          # The Works Team (factory team)
    "stadium":      "the BayArena",
    "title":        "Deutscher Meister",     # German Champion
    "unbeaten":     "Ungeschlagen",          # Unbeaten
    "chant":        "Oh Bayer Leverkusen, Schalalala!",
    "season":       "the Invincibles season",
}
