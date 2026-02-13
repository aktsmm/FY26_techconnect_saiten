"""Saiten MCP — Server entry point.

Creates the FastMCP server, registers tool modules, and starts the server.
Includes rate limiting, structured logging, and health monitoring.
"""

from __future__ import annotations

import logging
import pathlib
import time
from collections import defaultdict

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("saiten_mcp")

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
# Rate limiter — prevents GitHub API abuse
# ---------------------------------------------------------------------------
class RateLimiter:
    """Simple sliding-window rate limiter (per-tool).

    Default: 30 calls per 60-second window. Raises ValueError if exceeded.
    """

    def __init__(self, max_calls: int = 30, window_seconds: float = 60.0):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)

    def check(self, tool_name: str) -> None:
        """Check if a call is allowed. Raises ValueError if rate limited."""
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Prune old entries
        self._calls[tool_name] = [
            t for t in self._calls[tool_name] if t > window_start
        ]

        if len(self._calls[tool_name]) >= self.max_calls:
            raise ValueError(
                f"Rate limit exceeded for '{tool_name}': "
                f"{self.max_calls} calls per {self.window_seconds}s. "
                f"Please wait before retrying."
            )

        self._calls[tool_name].append(now)

    def reset(self) -> None:
        """Reset all rate limit counters (useful for testing)."""
        self._calls.clear()


rate_limiter = RateLimiter()

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
