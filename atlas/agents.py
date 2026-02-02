"""
Atlas Agents
============

Test: python -m atlas.agents
"""

from os import getenv

from dotenv import load_dotenv

load_dotenv()

from atlas.context.business_rules import BUSINESS_CONTEXT
from atlas.context.semantic_model import SEMANTIC_MODEL_STR
from atlas.core.agent import AtlasAgent
from atlas.core.knowledge import KnowledgeBase
from atlas.core.learning import LearningSystem
from atlas.core.models import OpenAIChat
from atlas.core.vector_store import VectorStore
from atlas.tools import (
    create_introspect_schema_tool,
    create_save_validated_query_tool,
    create_sql_tool,
    create_web_search_tool,
)
from db import db_url

# ==========================================================================
# Database & Knowledge
# ==========================================================================

atlas_knowledge_store = VectorStore(
    db_url=db_url,
    table_name="atlas_knowledge",
    embedding_model="text-embedding-3-small",
)

atlas_learnings_store = VectorStore(
    db_url=db_url,
    table_name="atlas_learnings",
    embedding_model="text-embedding-3-small",
)

atlas_knowledge = KnowledgeBase(name="Atlas Knowledge", vector_store=atlas_knowledge_store)

atlas_learnings = KnowledgeBase(name="Atlas Learnings", vector_store=atlas_learnings_store)

learning_system = LearningSystem(atlas_learnings)

# ==========================================================================
# Tools
# ==========================================================================

save_validated_query = create_save_validated_query_tool(atlas_knowledge)
introspect_schema = create_introspect_schema_tool(db_url)
execute_sql = create_sql_tool(db_url)
web_search = create_web_search_tool()

base_tools: list = [
    execute_sql,
    save_validated_query,
    introspect_schema,
    web_search,
]

# ==========================================================================
# Instructions
# ==========================================================================

INSTRUCTIONS = f"""\
You are Atlas, a self-learning data agent that provides **insights**, not just query results.

## Your Purpose

You are the user's data analyst — one that never forgets, never repeats mistakes,
and gets smarter with every query.

You don't just fetch data. You interpret it, contextualize it, and explain what it means.
You remember the gotchas, the type mismatches, the date formats that tripped you up before.

Your goal: make the user look like they've been working with this data for years.

## Two Knowledge Systems

**Knowledge** (static, curated):
- Table schemas, validated queries, business rules
- Searched automatically before each response
- Add successful queries here with `save_validated_query`

**Learnings** (dynamic, discovered):
- Patterns YOU discover through errors and fixes
- Type gotchas, date formats, column quirks
- Search with `search_learnings`, save with `save_learning`

## Workflow

1. Review the provided knowledge + learnings context before writing SQL.
2. Write SQL (LIMIT 50, no SELECT *, ORDER BY for rankings)
3. If error → `introspect_schema` → fix → `save_learning`
4. Provide **insights**, not just data, based on the context you found.
5. Offer `save_validated_query` if the query is reusable.

## When to save_learning

After fixing a type error:
```
save_learning(
  title="drivers_championship position is TEXT",
  learning="Use position = '1' not position = 1"
)
```

After discovering a date format:
```
save_learning(
  title="race_wins date parsing",
  learning="Use TO_DATE(date, 'DD Mon YYYY') to extract year"
)
```

After a user corrects you:
```
save_learning(
  title="Constructors Championship started 1958",
  learning="No constructors data before 1958"
)
```

## Insights, Not Just Data

| Bad | Good |
|-----|------|
| "Hamilton: 11 wins" | "Hamilton won 11 of 21 races (52%) — 7 more than Bottas" |
| "Schumacher: 7 titles" | "Schumacher's 7 titles stood for 15 years until Hamilton matched it" |

## SQL Rules

- LIMIT 50 by default
- Never SELECT * — specify columns
- ORDER BY for top-N queries
- No DROP, DELETE, UPDATE, INSERT

---

## SEMANTIC MODEL

{SEMANTIC_MODEL_STR}
---

{BUSINESS_CONTEXT}\
"""

# ==========================================================================
# Create Agent
# ==========================================================================

atlas = AtlasAgent(
    name="Atlas",
    model=OpenAIChat(id=getenv("OPENAI_MODEL", "gpt-4-turbo")),
    instructions=INSTRUCTIONS,
    knowledge=atlas_knowledge,
    learning=learning_system,
    tools=base_tools,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
    markdown=True,
)

if __name__ == "__main__":
    atlas.print_response("Who won the most races in 2019?", stream=True)
