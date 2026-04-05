"""Load and cache pre-computed CSV data for the dashboard."""

import json
from pathlib import Path

import pandas as pd

_DATA_DIR = Path(__file__).parent / "data"


def _load_metadata() -> dict:
    with open(_DATA_DIR / "metadata.json") as f:
        return json.load(f)


def _openalex_funder_url(funder_id: str) -> str:
    """Build OpenAlex funder URL from funder_id like 'F4320336376'."""
    return f"https://openalex.org/funders/{funder_id.lower()}"


def _load_funders(filename: str = "funders_summary_2024_2025.csv") -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / filename)
    # Build display label: "Funder Name (Country)"
    df["label"] = df.apply(
        lambda r: f"{r['funder_name']} ({r['country']})"
        if pd.notna(r["country"]) and r["country"]
        else r["funder_name"],
        axis=1,
    )
    # Build OpenAlex URL for funders with an ID
    df["openalex_url"] = df["funder_id"].apply(
        lambda x: _openalex_funder_url(x) if pd.notna(x) and x else ""
    )
    # Markdown link for data table: [Name](url)
    df["funder_link"] = df.apply(
        lambda r: f"[{r['funder_name']}]({r['openalex_url']})"
        if r["openalex_url"]
        else r["funder_name"],
        axis=1,
    )
    return df


def _load_journals(filename: str = "journals_summary_2024_2025.csv") -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / filename)
    # Ensure article count columns are integer
    for col in ["open_data_articles", "open_code_articles"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    return df


# Module-level cache — loaded once at import time
METADATA = _load_metadata()
FUNDERS = _load_funders()
FUNDERS_ALL_YEARS = _load_funders("funders_summary.csv")
JOURNALS = _load_journals()


def filter_by_min_articles(df: pd.DataFrame, min_articles: int) -> pd.DataFrame:
    return df[df["total_articles"] >= min_articles]


def filter_by_search(df: pd.DataFrame, query: str, col: str) -> pd.DataFrame:
    if not query:
        return df
    return df[df[col].str.contains(query, case=False, na=False)]
