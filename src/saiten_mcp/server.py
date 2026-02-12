"""Saiten MCP — Server entry point.

Creates the FastMCP server, registers tool modules, and starts the server.
"""

from __future__ import annotations

import pathlib

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Path resolution — all file paths are relative to project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Ensure required directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "rubrics").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="saiten-mcp",
    instructions="MCP server for the Agents League @ TechConnect scoring agent",
)

# ---------------------------------------------------------------------------
# Tool registration — auto-registered via @mcp.tool() on import
# ---------------------------------------------------------------------------
from saiten_mcp.tools import submissions  # noqa: E402, F401
from saiten_mcp.tools import rubrics      # noqa: E402, F401
from saiten_mcp.tools import scores       # noqa: E402, F401
from saiten_mcp.tools import reports      # noqa: E402, F401


def main() -> None:
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
