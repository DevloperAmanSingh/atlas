"""
Load Knowledge - Loads table metadata, queries, and business rules into knowledge base.

Usage:
    python -m atlas.scripts.load_knowledge             # Upsert (update existing)
    python -m atlas.scripts.load_knowledge --recreate  # Drop and reload all
"""

import argparse

from atlas.paths import KNOWLEDGE_DIR

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load knowledge into vector database")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop existing knowledge and reload from scratch",
    )
    args = parser.parse_args()

    from atlas.agents import atlas_knowledge

    if args.recreate:
        print("Recreating knowledge base (dropping existing data)...\n")
        atlas_knowledge.vector_store.drop()
        atlas_knowledge.vector_store.create()

    print(f"Loading knowledge from: {KNOWLEDGE_DIR}\n")

    for subdir in ["tables", "queries", "business"]:
        path = KNOWLEDGE_DIR / subdir
        if not path.exists():
            print(f"  {subdir}/: (not found)")
            continue

        files = [f for f in path.iterdir() if f.is_file() and not f.name.startswith(".")]
        print(f"  {subdir}/: {len(files)} files")

        if files:
            inserted = atlas_knowledge.load_from_directory(path)
            print(f"    inserted: {inserted}")

    print("\nDone!")
