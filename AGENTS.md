# AGENTS.md

## Project Overview
Atlas is a self-learning data agent for text-to-SQL and analytics. It grounds answers in multiple layers of context (schema metadata, business rules, known-good queries, runtime introspection, and learned fixes) and returns insights rather than raw rows.

This repo now uses a custom lightweight agent framework under `atlas/core` (no agno dependency).

## Architecture Snapshot
- **API**: FastAPI in `app/main.py` exposes `/query` and `/health`.
- **Agent**: `atlas/agents.py` builds a `AtlasAgent` with tools + knowledge + learnings.
- **Core framework**: `atlas/core/*`
  - `agent.py`: tool loop, retrieval context, CLI
  - `models.py`: OpenAI chat wrapper
  - `vector_store.py`: pgvector + hybrid search (semantic + keyword, RRF)
  - `knowledge.py`: KnowledgeBase wrapper
  - `learning.py`: LearningSystem (search + save)
  - `tools.py`: `@tool` decorator + OpenAI function schema
- **Tools**: `atlas/tools/*`
  - `sql.py`: read-only SQL execution tool
  - `introspect.py`: runtime schema inspection
  - `save_query.py`: save validated queries into knowledge
  - `web_search.py`: Exa API search
- **DB config**: `db/url.py` builds DB URL from env vars.

## Data + Knowledge Layout
```
atlas/knowledge/
  tables/      # JSON schema metadata
  queries/     # Known-good SQL patterns
  business/    # Metrics + rules
```

Vector tables created by `atlas/scripts/init_db.py`:
- `atlas_knowledge`
- `atlas_learnings`

## Environment Variables
Required:
- `OPENAI_API_KEY`

Optional:
- `EXA_API_KEY` (web search tool)
- `OPENAI_MODEL` (defaults to `gpt-4-turbo`)

Database (defaults in `db/url.py`):
- `DB_DRIVER` (default `postgresql+psycopg`)
- `DB_USER`
- `DB_PASS`
- `DB_HOST`
- `DB_PORT`
- `DB_DATABASE`

## Local Setup (venv + uv)
```
python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Common Commands
Initialize DB tables:
```
python -m atlas.scripts.init_db
```

Load knowledge:
```
python -m atlas.scripts.load_knowledge
```

Run CLI:
```
python -m atlas
```

Run API:
```
python -m app.main
```

## Notes for AI Contributors
- Do **not** reintroduce agno dependencies; use `atlas/core` abstractions instead.
- OpenAI clients should be created lazily (avoid requiring API keys at import time).
- SQL tool must remain **read-only** (no INSERT/UPDATE/DELETE/etc).
- Keep `.env` loading in entry points/scripts where needed (`atlas/agents.py`, `atlas/scripts/init_db.py`).
- Knowledge insertions should go through `KnowledgeBase` and avoid raw file system parsing outside `load_from_directory`.

## Testing/Verification
- Ensure `python -m atlas.scripts.init_db` works with env set.
- Ensure `python -m atlas.scripts.load_knowledge` completes and inserts files.
- API returns response for POST `/query`.
