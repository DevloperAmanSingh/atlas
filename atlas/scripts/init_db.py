"""Initialize pgvector tables for Atlas."""

from dotenv import load_dotenv

from atlas.core.vector_store import VectorStore
from db import db_url


def main() -> None:
    load_dotenv()
    stores = [
        VectorStore(db_url=db_url, table_name="atlas_knowledge"),
        VectorStore(db_url=db_url, table_name="atlas_learnings"),
    ]

    for store in stores:
        print(f"Ensuring table exists: {store.table_name}")
        store.create()

    print("Done.")


if __name__ == "__main__":
    main()
