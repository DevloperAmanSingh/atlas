"""
Atlas API
=========

Production deployment entry point for Atlas.

Run:
    python -m app.main
"""

from os import getenv

from fastapi import FastAPI
from pydantic import BaseModel

from atlas.agents import atlas

app = FastAPI(title="Atlas API")


class QueryRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.post("/query")
async def query(request: QueryRequest):
    response = atlas.run(request.message, stream=False)
    return {"response": response}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=getenv("RUNTIME_ENV", "prd") == "dev",
    )
