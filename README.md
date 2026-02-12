# Saiten — Agents League @ TechConnect 採点エージェント

> **提出トラック**: 🎨 Creative Apps — GitHub Copilot

## 概要

VS Code 上で `@saiten 採点して` と入力するだけで、Agents League @ TechConnect ハッカソンの全提出物を自動採点し、ランキングを生成するシステムです。

**GitHub Copilot カスタムエージェント** + **MCP (Model Context Protocol) サーバー** を組み合わせ、一貫性のある公平な審査を実現します。

## アーキテクチャ

```
┌─────────────────────────────────────────────┐
│  VS Code                                     │
│  ┌──────────────────────────────────────┐    │
│  │ 🤖 @saiten (Copilot Custom Agent)   │    │
│  │    saiten.agent.md                   │    │
│  └──────────┬───────────────────────────┘    │
│             │ MCP (stdio)                     │
│  ┌──────────▼───────────────────────────┐    │
│  │ ⚡ saiten-mcp (FastMCP Server)       │    │
│  │  ├ list_submissions()                │    │
│  │  ├ get_submission_detail()           │    │
│  │  ├ get_scoring_rubric()              │    │
│  │  ├ save_scores()                     │    │
│  │  └ generate_ranking_report()         │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
         │                    │
    ┌────▼────┐         ┌────▼────┐
    │ GitHub  │         │  Local  │
    │  API    │         │ Storage │
    └─────────┘         └─────────┘
```

## セットアップ

### 前提条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャー)
- [gh CLI](https://cli.github.com/) (GitHub CLI、認証済み)
- VS Code + GitHub Copilot

### インストール

```bash
# リポジトリをクローン
git clone <repo-url>
cd FY26_techconnect_saiten

# Python 仮想環境を作成
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージをインストール
uv pip install -e .

# gh CLI の認証確認
gh auth status
```

### VS Code 設定

`.vscode/mcp.json` が自動で MCP サーバーを設定します。追加設定は不要です。

## 使い方

VS Code のチャットパネルで以下のように入力します:

| コマンド | 説明 |
|---------|------|
| `@saiten 採点して` | 全提出物を一括採点 |
| `@saiten #48 を採点して` | 個別提出物を採点 |
| `@saiten ランキング出して` | ランキングレポートを生成 |
| `@saiten #48 を再採点して` | 個別提出物を再採点 |
| `@saiten Creative の採点基準は？` | 採点基準を表示 |

## プロジェクト構成

```
FY26_techconnect_saiten/
├── .github/agents/
│   └── saiten.agent.md           # Copilot カスタムエージェント
├── src/saiten_mcp/
│   ├── server.py                 # MCP Server エントリーポイント
│   ├── models.py                 # Pydantic データモデル
│   └── tools/
│       ├── submissions.py        # list_submissions, get_submission_detail
│       ├── rubrics.py            # get_scoring_rubric
│       ├── scores.py             # save_scores
│       └── reports.py            # generate_ranking_report
├── data/
│   ├── rubrics/                  # トラック別採点基準 (YAML)
│   └── scores.json               # 採点結果
├── reports/
│   └── ranking.md                # 自動生成ランキング
├── .vscode/mcp.json              # MCP サーバー設定
└── pyproject.toml
```

## 採点トラック

| トラック | 基準数 | 特記 |
|---------|-------|------|
| 🎨 Creative Apps | 5 基準 | Community Vote (10%) を除外し按分 |
| 🧠 Reasoning Agents | 5 基準 | 全体共通基準を採用 |
| 💼 Enterprise Agents | 3 基準 | 独自の 3 軸評価 |

## 技術スタック

- **Agent**: VS Code Copilot Custom Agent (`.agent.md`)
- **MCP Server**: Python 3.10+ / FastMCP
- **パッケージ管理**: uv
- **GitHub 連携**: gh CLI / GitHub REST API
- **データ**: JSON (スコア) / YAML (基準) / Markdown (レポート)

## ライセンス

MIT
