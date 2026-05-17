"""
data_loader.py
Bundesliga 2023/24 - Data loading and processing using Polars
"""

import polars as pl

DATA_URL = "https://www.football-data.co.uk/mmz4281/2324/D1.csv"

COLUMNS = [
    "Date", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG",         # Full-time goals
    "HTHG", "HTAG",         # Half-time goals
    "HS", "AS",             # Shots
    "HST", "AST",           # Shots on target
    "HC", "AC",             # Corners
    "HY", "AY",             # Yellow cards
    "HR", "AR",             # Red cards
    "PSH", "PSD", "PSA",    # Pinnacle odds (renamed below)
]

RENAME_MAP = {
    "PSH": "match_resultH",
    "PSD": "match_resultX",
    "PSA": "match_resultA",
}

NUMERIC_COLS = [
    "FTHG", "FTAG", "HTHG", "HTAG",
    "HS", "AS", "HST", "AST",
    "HC", "AC", "HY", "AY", "HR", "AR",
    "match_resultH", "match_resultX", "match_resultA",
]


def load_data() -> pl.DataFrame:
    """
    Fetch the CSV from football-data.co.uk, select required columns,
    rename odds columns, cast numerics, parse dates, and assign round numbers.

    Returns
    -------
    pl.DataFrame
        Fully processed Bundesliga 2023/24 dataframe with a 'Round' column.
    """
    # ── 1. Fetch & select ────────────────────────────────────────────────────
    raw = pl.read_csv(DATA_URL, infer_schema_length=0, null_values=["", "N/A"])
    data = raw.select(COLUMNS).rename(RENAME_MAP)

    # ── 2. Cast numeric columns ──────────────────────────────────────────────
    data = data.with_columns([
        pl.col(c).cast(pl.Float64, strict=False) for c in NUMERIC_COLS
    ])

    # ── 3. Parse dates  (format: DD/MM/YYYY) ────────────────────────────────
    data = data.with_columns(
        pl.col("Date").str.strptime(pl.Date, format="%d/%m/%Y", strict=False)
    )

    # ── 4. Sort chronologically ──────────────────────────────────────────────
    data = data.sort("Date")

    # ── 5. Assign round numbers (9 games per round, 34 rounds) ───────────────
    #   Row index 0-8 → Round 1, 9-17 → Round 2, … 297-305 → Round 34
    data = data.with_row_index(name="_row_idx").with_columns(
        ((pl.col("_row_idx") // 9) + 1).cast(pl.Int32).alias("Round")
    ).drop("_row_idx")

    return data


def get_round(data: pl.DataFrame, round_number: int) -> pl.DataFrame:
    """Return all matches for a given round."""
    return data.filter(pl.col("Round") == round_number)


def get_available_rounds(data: pl.DataFrame) -> list[int]:
    """Return sorted list of all round numbers in the dataset."""
    return sorted(data["Round"].unique().to_list())


if __name__ == "__main__":
    # Quick sanity check
    df = load_data()
    print(f"Total matches loaded: {df.shape[0]}")
    print(f"Rounds: {df['Round'].min()} to {df['Round'].max()}")
    print(f"\nColumns:\n{df.columns}")
    print(f"\nFirst 5 rows:\n{df.head(5)}")
    print(f"\nRound 34 ({df.filter(pl.col('Round') == 34).shape[0]} games):")
    print(df.filter(pl.col("Round") == 34).select(
        ["Round", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]
    ))
