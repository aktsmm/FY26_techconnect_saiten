"""Saiten MCP — Server entry point.

FastMCP サーバーを生成し、各ツールモジュールを登録して起動する。
"""

from __future__ import annotations

import pathlib

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# パス解決  — すべてのファイルパスはプロジェクトルート基準
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 必要なディレクトリを事前作成
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "rubrics").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FastMCP インスタンス
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="saiten-mcp",
    instructions="Agents League @ TechConnect 採点エージェント用 MCP サーバー",
)

# ---------------------------------------------------------------------------
# ツール登録  — 各モジュール import 時に @mcp.tool() で自動登録
# ---------------------------------------------------------------------------
from saiten_mcp.tools import submissions  # noqa: E402, F401
from saiten_mcp.tools import rubrics      # noqa: E402, F401
from saiten_mcp.tools import scores       # noqa: E402, F401
from saiten_mcp.tools import reports      # noqa: E402, F401


def main() -> None:
    """MCP サーバーを stdio transport で起動する."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
