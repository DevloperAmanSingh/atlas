"""Exa web search tool."""

from __future__ import annotations

import os

import httpx

from atlas.core.tools import tool


def create_web_search_tool():
    """Create Exa web search tool."""

    @tool
    def web_search(query: str, num_results: int = 5) -> str:
        """Search the web via Exa and return results as markdown."""
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            return "Error: EXA_API_KEY is not set."
        if not query or not query.strip():
            return "Error: query is required."
        if num_results <= 0:
            return "Error: num_results must be positive."

        payload = {
            "query": query,
            "num_results": num_results,
            "use_autoprompt": True,
            "type": "neural",
        }
        try:
            response = httpx.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": api_key},
                json=payload,
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return f"Error: web search failed - {exc}"

        data = response.json()
        results = data.get("results", [])
        if not results:
            return "No results found."

        lines = ["## Web Search Results", ""]
        for item in results:
            title = item.get("title") or "Untitled"
            url = item.get("url") or ""
            snippet = item.get("snippet") or ""
            lines.append(f"- **{title}**")
            if url:
                lines.append(f"  - {url}")
            if snippet:
                lines.append(f"  - {snippet}")

        return "\n".join(lines)

    return web_search
