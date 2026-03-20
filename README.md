# Ollama Autonomous Agent

Ollamaを使ってローカルで動作する自立型AIエージェント。Claude CLIのようにプロジェクトディレクトリから起動し、ファイル操作・コード実行・Web検索・長期記憶を備えたReActループで複雑なタスクを自律実行します。

---

## 特徴

- **完全ローカル動作** — Ollamaを使用。APIキー不要・データ外部送信なし
- **プロジェクト対応** — 起動ディレクトリを自動検出し、プロジェクトごとにセッション・メモリを分離
- **ReActループ** — Thought → Action（ツール呼び出し）→ Observation を繰り返し、複雑なタスクを自律実行
- **Plan-and-Execute** — 多段階タスクを自動でステップ分解して順次実行
- **長期記憶** — ChromaDBによるベクター検索で会話を跨いだ記憶を保持
- **セッション永続化** — SQLiteで会話履歴を保存し、再起動後も継続
- **豊富なツール** — ファイル操作・Pythonコード実行・Web検索・URL取得・記憶管理
- **Skills** — 再利用可能なプロンプトテンプレートを `/skill-name` で呼び出し。組み込み・ユーザー・プロジェクト単位で管理

---

## 必要環境

| ソフトウェア | バージョン | 用途 |
|---|---|---|
| Python | 3.11+ | 実行環境 |
| [Ollama](https://ollama.com) | 最新版 | ローカルLLM実行 |
| pipx | 任意 | グローバルコマンドとしてインストール |

### 推奨モデル

```bash
ollama pull qwen2.5:7b        # メインエージェント（VRAM 8GB以内）
ollama pull nomic-embed-text  # 長期メモリ用埋め込み
```

| モデル | VRAM目安 | 用途 |
|---|---|---|
| `qwen2.5:7b` | ~5GB | メイン（推奨） |
| `qwen2.5:14b` | ~10GB | 高精度が必要な場合 |
| `qwen2.5-coder:7b` | ~5GB | コーディング特化 |
| `nomic-embed-text` | ~300MB | 長期メモリの埋め込み |

---

## インストール

### pipx（推奨・グローバルインストール）

```bash
pip install pipx
pipx install git+https://github.com/fukui-yuto/agent.git
pipx ensurepath  # PATHに追加（初回のみ）
```

### ローカル開発

```bash
git clone https://github.com/fukui-yuto/agent.git
cd agent
pipenv install
pipenv run python -m agent
```

---

## 使い方

### 基本的な起動

```bash
cd /path/to/your-project
agent
```

起動ディレクトリを自動でプロジェクトルートとして認識します。セッションIDはプロジェクトパスから自動生成されるため、同じプロジェクトで起動するたびに会話履歴が復元されます。

### 起動オプション

```bash
agent [OPTIONS]

Options:
  -m, --model TEXT      使用するOllamaモデルを指定（例: qwen2.5:14b）
  -s, --session TEXT    セッションIDを手動指定（デフォルト: プロジェクトパスから自動生成）
  --no-memory           長期メモリを無効化
  --no-web              Web検索ツールを無効化
  --no-code             コード実行ツールを無効化
  --no-plan             Plan-and-Executeを無効化（シンプルなReActループのみ）
```

```bash
# モデル変更
agent --model qwen2.5:14b

# 別セッションで起動（過去の会話と切り離す）
agent --session fresh-start

# Web検索とコード実行を無効にして軽量起動
agent --no-web --no-code
```

### スラッシュコマンド

| コマンド | 説明 |
|---|---|
| `/init` | `AGENT.md` を作成してプロジェクト固有の指示を記述 |
| `/status` | 現在のプロジェクト・セッション・モデル・スキル情報を表示 |
| `/clear` | 現在のセッションの会話履歴を削除 |
| `/memory` | このプロジェクトの長期記憶一覧を表示 |
| `/sessions` | 保存されているセッション一覧を表示 |
| `/skills` | 利用可能なスキル一覧を表示 |
| `/skill new <name>` | 新しいスキルを対話形式で作成 |
| `/skill reload` | スキルをディスクから再読み込み |
| `/<skill-name>` | スキルを呼び出す（例: `/commit`、`/review`） |
| `/help` | コマンド一覧を表示 |
| `/exit` | エージェントを終了 |

---

## AGENT.md によるプロジェクトカスタマイズ

プロジェクトルートに `AGENT.md` を置くと、エージェント起動時に自動で読み込まれます。Claude CLIの `CLAUDE.md` に相当します。

```bash
agent
> /init   # AGENT.md を自動生成
```

```markdown
<!-- AGENT.md の例 -->
# Project Instructions

## プロジェクト概要
FastAPIを使ったREST APIサーバー。

## コーディング規約
- Python 3.11+、型ヒント必須
- テストはpytestで記述
- コミットメッセージはConventional Commits形式

## 重要事項
- データベースはPostgreSQL（環境変数 DATABASE_URL で接続）
- 本番環境へのデプロイはGitHub Actionsで自動化済み
```

---

## Skills

スキルは `/skill-name` で呼び出せる再利用可能なプロンプトテンプレートです。よく使うタスクをスキルとして定義しておくことで、毎回指示を書かずに一発で実行できます。

### 組み込みスキル

| スキル | 説明 |
|---|---|
| `/commit` | ステージ済みの変更を分析して適切なgitコミットを作成 |
| `/review` | git差分をコードレビュー（バグ・セキュリティ・可読性） |
| `/test` | プロジェクトのテストを実行して結果を報告 |
| `/summarize` | プロジェクトの構成とコードベースを分析してサマリー |
| `/fix` | エラー・バグを診断して修正 |
| `/docs` | docstring・READMEを生成・更新 |

### スキルの呼び出し

```bash
/commit                    # コミットスキルを実行
/review                    # コードレビューを実行
/fix TypeError: ...        # 追加の文脈を渡して実行
```

### カスタムスキルの作成

```bash
/skill new deploy          # 対話形式で新しいスキルを作成（~/.agent/skills/ に保存）
```

またはファイルを直接作成することもできます。

```markdown
<!-- .skills/deploy.md — プロジェクト固有スキル -->
---
name: deploy
description: 本番環境にデプロイする
---
テストを実行し、問題なければビルドして本番環境にデプロイしてください。
デプロイ後はヘルスチェックを確認してください。
```

### スキルの読み込み優先順位

```
<project>/.skills/*.md    ← プロジェクト固有（最優先）
~/.agent/skills/*.md      ← ユーザー共通
agent/skills/builtin/     ← 組み込み（最低優先）
```

同名のスキルはより上位のものが優先されるため、組み込みスキルをプロジェクトやユーザーレベルで上書きできます。

### スキルファイルの形式

```markdown
---
name: スキル名
description: スキルの説明（/skills 一覧に表示）
---
ここにプロンプト本文を記述します。
エージェントに実行させたい内容を自然言語で書いてください。
```

フロントマターは省略可能です。省略した場合はファイル名がスキル名になります。

---

## 利用可能な機能

エージェントは会話の文脈から必要な操作を自律的に判断して実行します。ツール名を指定する必要はありません。

| カテゴリ | できること |
|---|---|
| ファイル操作 | ファイルの読み書き・作成・ディレクトリ一覧・ファイル検索 |
| コード実行 | Pythonコードをその場で実行して結果を返す |
| Web検索 | DuckDuckGoで検索、URLのコンテンツを取得 |
| 長期メモリ | 情報を記憶・検索（会話をまたいで保持） |
| ユーティリティ | 日時取得、数式計算 |

> コード実行は `import os` / `import sys` / `import subprocess` などの危険な操作をブロックします。

---

## アーキテクチャ

```
起動ディレクトリ（プロジェクトルート）
        │
        ▼
  main.py (CLI)
        │
        ▼
  Orchestrator（ReActループ）
  ├── LLMClient（Ollama API）
  ├── ToolRegistry（ツール管理・実行）
  ├── ShortTermMemory（会話履歴）
  ├── LongTermMemory（ChromaDB）
  ├── Planner（Plan-and-Execute）
  └── SessionManager（SQLite永続化）
```

### ReActループの流れ

```
ユーザー入力
    │
    ├─► [Planner] 複雑なタスクか判定
    │       │ 複数ステップ → サブタスクに分解して順次実行
    │       │ シンプル    → そのままReActループへ
    │
    ▼
[Ollama LLM] ツールスキーマを渡してチャット
    │
    ├─ ツール呼び出し ──► [Tool Executor] 実行 ──► 結果を履歴に追加 ──► LLMへ
    │
    └─ テキスト回答 ──► ユーザーへ出力
                            │
                            ▼
                    [LongTermMemory] 会話を自動保存
                    [SessionManager] 履歴をSQLiteに保存
```

### メモリの種類

| 種類 | 保存先 | 説明 |
|---|---|---|
| 短期メモリ | メモリ上 | 現在の会話履歴（最大50件、超過時は自動圧縮） |
| 長期メモリ | `~/.agent/chroma/` | ChromaDBによるベクター検索（プロジェクト別） |
| セッション | `~/.agent/sessions.db` | SQLiteによる会話履歴の永続化 |

---

## ディレクトリ構成

```
agent/
├── agent/
│   ├── __main__.py          # エントリポイント（Windows UTF-8対応）
│   ├── main.py              # CLI（Typer + Rich REPL）
│   ├── config.py            # 設定管理・プロジェクト検出
│   ├── core/
│   │   ├── orchestrator.py  # ReActループ制御（中核）
│   │   ├── planner.py       # Plan-and-Execute
│   │   └── session.py       # SQLiteセッション永続化
│   ├── llm/
│   │   ├── client.py        # Ollama APIクライアント
│   │   ├── parser.py        # ツール呼び出しパーサー
│   │   └── prompts.py       # システムプロンプト（AGENT.md読み込み）
│   ├── memory/
│   │   ├── short_term.py    # 会話履歴（ローリングウィンドウ）
│   │   ├── long_term.py     # ChromaDB長期メモリ
│   │   └── compressor.py    # 長い会話の自動要約圧縮
│   ├── tools/
│   │   ├── base.py          # @toolデコレータ・スキーマ自動生成
│   │   ├── registry.py      # ツール登録・実行ディスパッチャー
│   │   ├── system_tools.py  # 日時・計算
│   │   ├── file_tools.py    # ファイル操作
│   │   ├── code_tools.py    # Pythonコード実行
│   │   ├── web_tools.py     # Web検索・URL取得
│   │   └── memory_tools.py  # 記憶操作
│   ├── skills/
│   │   ├── manager.py       # スキル読み込み・管理
│   │   └── builtin/         # 組み込みスキル（.mdファイル）
│   └── utils/
│       └── logger.py        # Richロガー（Windows UTF-8対応）
├── .skills/                 # プロジェクト固有スキル（任意）
├── AGENT.md                 # プロジェクト固有の指示（任意）
├── .env                     # 環境変数（gitignore対象）
├── .env.example             # 環境変数テンプレート
├── Pipfile                  # pipenv依存関係
└── pyproject.toml           # パッケージ定義
```

---

## 設定

`.env` ファイルをプロジェクトルートに作成することで設定を上書きできます（`.env.example` を参照）。

```bash
cp .env.example .env
```

| 環境変数 | デフォルト | 説明 |
|---|---|---|
| `AGENT_OLLAMA_HOST` | `http://localhost:11434` | OllamaサーバーのURL |
| `AGENT_MAIN_MODEL` | `qwen2.5:7b` | 使用するモデル |
| `AGENT_EMBED_MODEL` | `nomic-embed-text` | 埋め込みモデル |
| `AGENT_MAX_ITERATIONS` | `20` | ReActループの最大ステップ数 |
| `AGENT_MAX_HISTORY` | `50` | 短期メモリの最大メッセージ数 |
| `AGENT_ENABLE_WEB_SEARCH` | `true` | Web検索ツールの有効/無効 |
| `AGENT_ENABLE_CODE_EXECUTION` | `true` | コード実行ツールの有効/無効 |
| `AGENT_ENABLE_LONG_TERM_MEMORY` | `true` | 長期メモリの有効/無効 |

---

## データの保存場所

すべてのデータはホームディレクトリの `~/.agent/` に保存されます。プロジェクト間で干渉しません。

```
~/.agent/
├── chroma/          # ChromaDB（長期メモリ、プロジェクト別コレクション）
├── sessions.db      # SQLite（会話履歴）
└── skills/          # ユーザー共通スキル（手動または /skill new で作成）
```

---

## アップデート

```bash
pipx install git+https://github.com/fukui-yuto/agent.git --force
```

---

## ライセンス

MIT
