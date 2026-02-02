"""CLI entry point: python -m atlas"""

from atlas.agents import atlas

if __name__ == "__main__":
    atlas.cli_app(stream=True)
