# Atlas

Atlas is a self-learning data agent for text-to-SQL and analytics. It grounds answers in multiple layers of context (schema metadata, business rules, known-good queries, runtime introspection, and learned fixes) and returns insights, not just rows.

**What Atlas does**
- Translates natural language questions into safe, read-only SQL
- Uses curated knowledge and runtime introspection to avoid mistakes
- Learns from fixes and reuses proven queries
- Summarizes results into business-ready insights

## Architecture

Atlas is built as a lightweight agent framework that runs tools, retrieves context, and learns over time.

**API**
- `app/main.py`: FastAPI app exposing `/query` and `/health`

**Agent**
- `atlas/agents.py`: constructs an `AtlasAgent` with tools, knowledge, and learnings

**Core Framework** (`atlas/core`)
- `agent.py`: tool loop, retrieval context, CLI
- `models.py`: OpenAI chat wrapper
- `vector_store.py`: pgvector + hybrid search (semantic + keyword, RRF)
- `knowledge.py`: KnowledgeBase wrapper
- `learning.py`: LearningSystem (search + save)
- `tools.py`: `@tool` decorator + OpenAI function schema

**Tools** (`atlas/tools`)
- `sql.py`: read-only SQL execution tool
- `introspect.py`: runtime schema inspection
- `save_query.py`: save validated queries into knowledge
- `web_search.py`: Exa API search

**Knowledge Layout**
```
atlas/knowledge/
  tables/      # JSON schema metadata
  queries/     # Known-good SQL patterns
  business/    # Metrics + rules
```

Vector tables created by `atlas/scripts/init_db.py`:
- `atlas_knowledge`
- `atlas_learnings`

## How Atlas Answers Questions

1. Pulls relevant knowledge and learnings
2. Writes SQL with safe defaults (LIMIT 50, no `SELECT *`)
3. Introspects schema when needed
4. Executes read-only SQL and interprets results
5. Produces insights and can save reusable queries

## Setup

**Requirements**
- Python 3.11+
- PostgreSQL with `pgvector` installed
- `OPENAI_API_KEY` in the environment

**Optional**
- `EXA_API_KEY` for web search
- `OPENAI_MODEL` (defaults to `gpt-4-turbo`)

**Database Environment Variables** (defaults in `db/url.py`)
- `DB_DRIVER` (default `postgresql+psycopg`)
- `DB_USER`
- `DB_PASS`
- `DB_HOST`
- `DB_PORT`
- `DB_DATABASE`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Initialize Vector Tables

```bash
python -m atlas.scripts.init_db
```

## Load Knowledge

```bash
python -m atlas.scripts.load_knowledge
# Or to rebuild from scratch
python -m atlas.scripts.load_knowledge --recreate
```

## Run CLI

```bash
python -m atlas
```

## Run API

```bash
python -m app.main
```

API endpoints:
- `POST /query` with JSON `{ "message": "..." }`
- `GET /health`

## Optional: Load IMDB Sample Data

```bash
python -m atlas.scripts.load_imdb
```

## Notes

- OpenAI clients are created lazily; API keys are required at runtime, not import time.
- The SQL tool is read-only. Avoid introducing write operations.
- Knowledge insertions should go through `KnowledgeBase` and `load_from_directory`.

