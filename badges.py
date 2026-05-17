"""
badges.py  -  Pure SVG team badge circles, no external images needed.
Always renders correctly in Streamlit unsafe_allow_html.
"""

# Brand colours for each team
TEAM_COLORS = {
    "Bayern Munich":  ("#dc052d", "#ffffff"),   # (bg, text)
    "Dortmund":       ("#fde100", "#000000"),
    "RB Leipzig":     ("#dd0741", "#ffffff"),
    "Leverkusen":     ("#e32221", "#000000"),
    "Ein Frankfurt":  ("#e1000f", "#ffffff"),
    "Stuttgart":      ("#e32221", "#ffffff"),
    "Hoffenheim":     ("#1761a7", "#ffffff"),
    "Wolfsburg":      ("#65b32e", "#ffffff"),
    "Freiburg":       ("#e1000f", "#ffffff"),
    "Werder Bremen":  ("#1d9f4f", "#ffffff"),
    "Heidenheim":     ("#c0392b", "#ffffff"),
    "Darmstadt":      ("#005ca9", "#ffffff"),
    "M'gladbach":     ("#1a1a1a", "#ffffff"),
    "Union Berlin":   ("#e32221", "#ffffff"),
    "Bochum":         ("#005ca9", "#ffffff"),
    "Augsburg":       ("#ba3733", "#ffffff"),
    "Mainz":          ("#c3112d", "#ffffff"),
    "FC Koln":        ("#e32221", "#ffffff"),
    "Koln":           ("#e32221", "#ffffff"),
}

def _initials(team: str) -> str:
    words = team.replace("'", "").replace(".", "").split()
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()

def badge_svg(team: str, size: int = 26) -> str:
    """Return a self-contained SVG badge circle — always renders in Streamlit."""
    bg, fg = TEAM_COLORS.get(team, ("#d20515", "#ffffff"))
    initials = _initials(team)
    r = size // 2
    fs = max(size // 3, 7)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;display:inline-block;vertical-align:middle;">'
        f'<circle cx="{r}" cy="{r}" r="{r-1}" fill="{bg}" '
        f'stroke="rgba(255,255,255,0.18)" stroke-width="1"/>'
        f'<text x="{r}" y="{r + fs//3}" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-weight="bold" '
        f'font-size="{fs}" fill="{fg}">{initials}</text>'
        f'</svg>'
    )
