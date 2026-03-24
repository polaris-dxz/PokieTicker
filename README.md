# PokieTicker — Understand the "Why" Behind Every Price Move

**🔗 Live Demo: [mitrui.com/PokieTicker](https://mitrui.com/PokieTicker/)** | [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?logo=buymeacoffee)](https://buymeacoffee.com/mitrui)

Since I wanted to understand the stories behind candlestick charts, I vibe coded this app.

As a stock market beginner, the news was too fragmented and I was wasting a lot of time, never understanding why prices went up or down. I built PokieTicker to develop **event-driven thinking** — to understand the "why" behind every price move.

<!-- Replace YOUR_TWEET_URL with your actual X post URL -->
[![Watch Demo](docs/demo.gif)](YOUR_TWEET_URL)

> Click to watch the full demo video

## What It Does

- **News on the chart** — Dots on the candlestick chart represent news for each date. Click any dot to see the news impacting that company at the time.
- **Filter by impact type** — Market, earnings, product, policy, competition, or management. Click a category to see related bullish or bearish news.
- **Find similar events** — Discover historical days with similar news patterns and see what happened to the stock afterward.
- **AI explains price moves** — Select a date range and ask AI why the stock dropped or rallied. It tells you what events caused it.
- **Predict trends** — Based on the past 30 days of news events, the model predicts how these events might affect future price direction.

![screenshot](docs/screenshot.png)

## How the Prediction Works

PokieTicker includes an XGBoost-based prediction system that combines news sentiment with technical indicators:

**Features (31 total):**
- **News features** — article count, sentiment score, positive/negative ratio, 3/5/10-day rolling averages, sentiment momentum
- **Technical features** — price returns (1/3/5/10-day), volatility, volume ratio, RSI-14, moving average crossover

**How it works:**
1. News articles are scored for sentiment by Claude Haiku (batch API) — each article gets a sentiment label, key discussion summary, and bullish/bearish reasons
2. These are combined with OHLC price data into daily feature vectors
3. XGBoost classifiers predict up/down direction at T+1, T+3, and T+5 horizons
4. The system also finds historically similar periods (cosine similarity on feature vectors) and shows what happened next

**Why news-driven prediction can work:**
- Stock prices are driven by information. Major news events (earnings, policy changes, product launches) create predictable short-term momentum
- Sentiment clustering matters — when multiple negative articles cluster on the same day, the downward pressure tends to persist for 1-3 days
- Historical pattern matching works because markets react similarly to similar events (e.g., tariff announcements, FDA approvals, earnings beats)

> This is an experimental tool for learning, not financial advice. Markets are complex and no model captures everything.

## Architecture

```
Frontend (React + Vite + D3.js)          Backend (FastAPI + SQLite)
+---------------------------------+      +----------------------------+
|  CandlestickChart (D3.js)       |      |  /api/stocks/{sym}/ohlc    |
|  +- news dots on each date      |----->|  /api/news/{sym}?date=     |
|  +- crosshair + click to lock   |      |  /api/news/{sym}/categories|
|                                  |      |                            |
|  NewsPanel (right sidebar)       |<-----|  SQLite: .data/pokieticker.db |
|  +- sentiment sorted             |      |  +- ohlc (51K+ rows)      |
|  +- up/down reasons              |      |  +- news_raw (61K+)       |
|  +- T+1/T+5 returns              |      |  +- layer1_results (97K+) |
|                                  |      |                            |
|  PredictionPanel                 |<-----|  /api/predict/{sym}/forecast|
|  +- 7-day & 30-day forecasts     |      |  +- XGBoost models         |
|  +- similar historical periods   |      |  +- cosine similarity      |
+---------------------------------+      +----------------------------+
```

## Data Pipeline

```
Polygon API --> Layer 0 (rule filter) --> Layer 1 (Haiku Batch API) --> Layer 2 (Sonnet, on-demand)
  OHLC + News    reject spam/listicles    sentiment + up/down reasons     deep analysis on click
                  ~17% rejected            50 articles per batch call      cached in DB
```

## Quick Start

> 想**免费部署到公网**？见 [docs/deploy.md](docs/deploy.md)（Render / Fly.io / 自建）。

The repo includes a pre-built database (`.data/pokieticker.db` or `pokieticker.db.gz`) with historical data, so you can run it immediately — **no API keys needed**.

### Option A: Install script (uv + pnpm)

Requires [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io/) installed.

```bash
git clone https://github.com/owengetinfo-design/PokieTicker.git
cd PokieTicker
./install.sh           # install only
./install.sh --start   # install and start both server + app
```

Then open **http://localhost:7777/PokieTicker/** (if you used `--start`).

### Option B: Manual setup

```bash
git clone https://github.com/owengetinfo-design/PokieTicker.git
cd PokieTicker

# Unpack the pre-built database (into .data/)
mkdir -p .data && (test -f pokieticker.db.gz && gunzip -k -c pokieticker.db.gz > .data/pokieticker.db || true)

# Server (Python 3.10+) with uv
uv venv && uv pip install -r requirements.txt

# App (Node.js 18+) with pnpm
cd app && pnpm install && cd ..
```

Then start both services (in two terminal windows):

```bash
# Terminal 1: Server
uv run uvicorn server.api.main:app --reload

# Terminal 2: App
cd app && pnpm run dev
```

Open **http://localhost:7777/PokieTicker/** and you're done.

> **Just want to see the demo?** Visit [mitrui.com/PokieTicker](https://mitrui.com/PokieTicker/) — no setup needed.

### Updating data (optional)

If you want to fetch the latest stock data and run AI analysis, you'll need API keys:

```bash
cp .env.example .env
# Edit .env and fill in your keys:
```

| Key | Where to get it | Cost |
|-----|-----------------|------|
| `POLYGON_API_KEY` | [polygon.io](https://polygon.io/) | Free tier |
| `ANTHROPIC_BASE_URL` | 默认 `https://api.apiyi.com`（[API易](https://apiyi.com) Anthropic 兼容网关，**不要**带 `/v1`）；官方填 `https://api.anthropic.com` | — |
| `ANTHROPIC_API_KEY` | 与 `ANTHROPIC_BASE_URL` 对应：API易控制台或 [Anthropic Console](https://console.anthropic.com/) | 按服务商计费 |

一键更新（推荐）：

```bash
./update_data.sh           # 增量更新 OHLC + 新闻；成功后 gzip → .data/pokieticker.db.gz，并 git commit + push
./update_data.sh --no-git  # 同上但不执行 git（适合 cron / 无 push 凭证）
./update_data.sh --full    # 全量拉取
./update_data.sh --layer1  # 增量 + 提交 Layer 1 Batch（终端会打印 batch_id，再执行 batch_collect）
./update_data.sh --full --layer1
```

成功结束后会把数据库打成 **`.data/pokieticker.db.gz`**（仓库通过 `.gitignore` 的 `!.data/pokieticker.db.gz` 跟踪该文件）。默认会尝试提交并 `git push`；若当前目录不是 Git 仓库、或压缩包相对上次提交无变化，则会跳过相应步骤。

或手动执行：

```bash
# Fetch new OHLC + news
python -m server.bulk_fetch

# Run AI analysis
python -m server.batch_submit --top 50
python -m server.batch_collect <batch_id>
```

## Project Structure

```
.env                          # API keys (gitignored)
.data/                        # Data directory (db, models, cache; 默认忽略，例外见 .gitignore 中的 pokieticker.db.gz)
requirements.txt              # Python dependencies

server/                       # Python package (API + pipeline + ML)
  config.py                   # pydantic-settings, .data paths, .env
  database.py                 # 9-table SQLite schema
  bulk_fetch.py               # Bulk download OHLC + news for many tickers
  batch_submit.py             # Submit Layer 1 to Anthropic Batch API
  batch_collect.py            # Collect Batch API results
  weekly_update.py            # Incremental weekly data update
  polygon/
    client.py                 # Polygon API with retry/backoff
  pipeline/
    layer0.py                 # Rule-based filter (free)
    layer1.py                 # Claude Haiku batch analysis
    layer2.py                 # Sonnet on-demand deep analysis
    alignment.py              # News -> trading day + forward returns
    similarity.py             # Similar news pattern matching
  ml/
    features.py               # 31-feature engineering (news + technical)
    model.py                  # XGBoost training (per-ticker + unified)
    inference.py              # Forecast generation + similar period analysis
    backtest.py               # Backtesting framework
    lstm_model.py             # Experimental LSTM model
  api/
    main.py                   # FastAPI app + CORS
    routers/
      stocks.py               # GET /api/stocks, /search, /{sym}/ohlc
      news.py                 # GET /api/news/{sym}, /{sym}/timeline
      analysis.py             # POST /api/analysis/deep, /story
      pipeline.py             # POST /api/pipeline/fetch, /process
      predict.py              # GET /api/predict/{sym}/forecast

skills/                      # OpenClaw skills（可选）
  pokieticker/               # 查询标的、OHLC、新闻、预测等
    manifest.json
    index.mjs

app/                          # UI (React + Vite; shared by web and future desktop)
  src/
    App.tsx                   # Main layout (chart + panels)
    components/
      CandlestickChart.tsx    # D3.js chart with news dots
      NewsPanel.tsx           # Sentiment-sorted news cards
      NewsCategoryPanel.tsx   # Filter by impact category
      PredictionPanel.tsx     # AI forecast + similar periods
      RangeQueryPopup.tsx     # "Why did it drop?" range analysis
      SimilarDaysPanel.tsx    # Historical pattern matches
      StockSelector.tsx       # Ticker search + tabs
```

## OpenClaw Skill

可将 PokieTicker 作为 [OpenClaw](https://github.com/OpenClaw/OpenClaw) 的 Skill 使用，通过 `action` 调用列表、OHLC、新闻、分类、预测等接口。安装与配置见 [skills/pokieticker/README.md](skills/pokieticker/README.md)；在 OpenClaw 的 Secrets 中设置 `POKIETICKER_BASE_URL`（默认 `http://localhost:8000`）即可指定后端地址。

## Weekly Update

```bash
./update_data.sh           # 增量更新（等价于 weekly_update）
./update_data.sh --layer1  # 再提交 Layer 1，按终端提示执行 batch_collect <batch_id>
```

## Cost Summary

| Item | Cost |
|------|------|
| Polygon data (free tier) | $0 |
| Layer 1 Batch API (per 1000 articles) | ~$0.35 |
| Layer 2 on-demand (per article) | ~$0.003 |
| Weekly incremental update | ~$1-2 |

## Tech Stack

- **App (UI)**: React, TypeScript, Vite, D3.js
- **Server**: FastAPI, SQLite (WAL mode), Pydantic
- **AI**: Claude Haiku 4.5 (batch sentiment), Claude Sonnet (deep analysis)
- **ML**: XGBoost (prediction), cosine similarity (pattern matching)
- **Data**: Polygon.io REST API

## License

MIT — see [LICENSE](LICENSE) for details.
