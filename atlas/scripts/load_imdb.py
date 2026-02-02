"""Load IMDB datasets into PostgreSQL.

Downloads and loads official IMDB data from https://datasets.imdbws.com/

Tables created:
- titles: Basic title information (movies, TV shows, episodes)
- ratings: User ratings and vote counts
- people: Actors, directors, writers, crew
- principals: Cast and crew for each title (relationships)
- crew: Directors and writers for each title

Usage:
    python -m atlas.scripts.load_imdb
"""

import gzip
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from db import db_url

DATA_DIR = Path("data/imdb")


def load_imdb_data():
    """Load IMDB datasets."""
    engine = create_engine(db_url)

    print("Loading IMDB data...\n")

    # 1. Title Basics (movies, TV shows, etc.)
    print("Loading titles...")
    df_titles = pd.read_csv(
        DATA_DIR / "title.basics.tsv",
        sep="\t",
        na_values="\\N",
        dtype={"startYear": "Int64", "endYear": "Int64", "runtimeMinutes": "Int64"},
    )
    # Filter to movies and TV series only (reduce size)
    df_titles = df_titles[df_titles["titleType"].isin(["movie", "tvSeries", "tvMiniSeries"])]
    df_titles.to_sql("titles", engine, if_exists="replace", index=False, chunksize=10000)
    print(f"  ✓ {len(df_titles):,} titles\n")

    # 2. Ratings
    print("Loading ratings...")
    df_ratings = pd.read_csv(DATA_DIR / "title.ratings.tsv", sep="\t")
    df_ratings.to_sql("ratings", engine, if_exists="replace", index=False, chunksize=10000)
    print(f"  ✓ {len(df_ratings):,} ratings\n")

    # 3. People (actors, directors, etc.)
    print("Loading people...")
    df_people = pd.read_csv(
        DATA_DIR / "name.basics.tsv",
        sep="\t",
        na_values="\\N",
        dtype={"birthYear": "Int64", "deathYear": "Int64"},
    )
    # Limit to people with known professions (reduce size)
    df_people = df_people[df_people["knownForTitles"].notna()]
    df_people.to_sql("people", engine, if_exists="replace", index=False, chunksize=10000)
    print(f"  ✓ {len(df_people):,} people\n")

    # 4. Principals (cast/crew per title)
    print("Loading principals (cast & crew)...")
    df_principals = pd.read_csv(
        DATA_DIR / "title.principals.tsv",
        sep="\t",
        na_values="\\N",
    )
    # Only keep principals for titles we loaded
    df_principals = df_principals[df_principals["tconst"].isin(df_titles["tconst"])]
    df_principals.to_sql("principals", engine, if_exists="replace", index=False, chunksize=10000)
    print(f"  ✓ {len(df_principals):,} principal credits\n")

    # 5. Crew (directors/writers)
    print("Loading crew...")
    df_crew = pd.read_csv(DATA_DIR / "title.crew.tsv", sep="\t", na_values="\\N")
    df_crew = df_crew[df_crew["tconst"].isin(df_titles["tconst"])]
    df_crew.to_sql("crew", engine, if_exists="replace", index=False, chunksize=10000)
    print(f"  ✓ {len(df_crew):,} crew records\n")

    # Create indexes for better query performance
    print("Creating indexes...")
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_titles_type ON titles(titleType)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_titles_year ON titles(startYear)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ratings_tconst ON ratings(tconst)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_principals_tconst ON principals(tconst)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_principals_nconst ON principals(nconst)"))
        conn.commit()
    print("  ✓ Indexes created\n")

    print("Done! IMDB data loaded successfully.")
    print(
        f"\nTotal: {len(df_titles):,} titles, {len(df_ratings):,} ratings, "
        f"{len(df_people):,} people, {len(df_principals):,} credits"
    )


if __name__ == "__main__":
    load_imdb_data()
