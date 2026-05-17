# ⚽ Bundesliga 2023/24 Dashboard — Phase 2

## Project Structure

```
bundesliga_dashboard/
├── app.py            # Streamlit app (main entry point)
├── data_loader.py    # Data fetching & processing with Polars
├── requirements.txt  # Dependencies
└── README.md
```

## Setup (Windows)

### 1. Install dependencies
```bash
pip install polars streamlit
```

### 2. Run the app
```bash
cd bundesliga_dashboard
streamlit run app.py
```

The app will open automatically at http://localhost:8501

## Data

- **Source**: https://www.football-data.co.uk/mmz4281/2324/D1.csv
- Fetched live on startup (cached for 1 hour)
- No manual download needed

## Columns Used

| Column | Description |
|--------|-------------|
| Date | Match date |
| HomeTeam / AwayTeam | Team names |
| FTHG / FTAG | Full-time goals (Home / Away) |
| HTHG / HTAG | Half-time goals |
| HS / AS | Total shots |
| HST / AST | Shots on target |
| HC / AC | Corners |
| HY / AY | Yellow cards |
| HR / AR | Red cards |
| match_resultH/X/A | Pinnacle pre-match odds (renamed from PSH/PSD/PSA) |
| Round | Matchday 1–34 (9 games per round, sorted by date) |

## Features
- 🔢 Filter by Matchday (Round 1–34)
- ⭐ Round 34 marked as Final Round
- 📋 Expandable match summary per game with stat bars
- 💰 Pre-match odds with winner highlighted in green
- 🃏 Yellow/Red card visualisation
