from __future__ import annotations

from fastapi import FastAPI, APIRouter
from fastapi_mcp import FastApiMCP


def setup_mcp_server(
    app: FastAPI,
    mount_path: str = "/mcp",
    include_tags: list[str] | None = None,
) -> FastApiMCP:
    mcp = FastApiMCP(
        app,
        name="Enterprise RAG MCP Server",
        description="MCP server exposing RAG query, document management, and Bible search tools for AI assistants.",
        describe_all_responses=False,
        describe_full_response_schema=False,
    )

    mcp.mount_http(mount_path=mount_path)

    return mcp
