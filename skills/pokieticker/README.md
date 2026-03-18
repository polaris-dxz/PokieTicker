# PokieTicker OpenClaw Skill

将 PokieTicker 后端以 Skill 形式接入 [OpenClaw](https://github.com/OpenClaw/OpenClaw)，通过 `action` 与可选参数调用股票列表、OHLC、新闻、分类与预测等接口。

## 安装

OpenClaw 会从 **`~/.openclaw/skills/`** 加载本机 skill，目录名需与 `manifest.json` 里的 `name` 一致（即 `pokieticker`）。本仓库中 skill 位于 `skills/pokieticker/`。目录内需包含 **SKILL.md**（含 name、description），OpenClaw 才会将其列为「已安装的 skill」并供 Agent 选用；`manifest.json` 与 `index.mjs` 为实际调用后端 API 的配置与实现。

**方式一：复制或符号链接到标准目录（推荐）**

```bash
# 复制
mkdir -p ~/.openclaw/skills
cp -r /path/to/PokieTicker/skills/pokieticker ~/.openclaw/skills/

# 或符号链接（便于后续拉仓库更新）
mkdir -p ~/.openclaw/skills
ln -s /path/to/PokieTicker/skills/pokieticker ~/.openclaw/skills/pokieticker
```

**方式二：通过配置额外目录加载**

在 `~/.openclaw/openclaw.json` 的 `skills.load.extraDirs` 里加入本仓库的 **`skills`** 目录（这样 OpenClaw 会直接看到 `pokieticker` 子目录）：

```json
{
  "skills": {
    "load": {
      "extraDirs": ["/path/to/PokieTicker/skills"]
    }
  }
}
```

安装后确保 PokieTicker 后端已启动（默认 `http://localhost:8000`），OpenClaw 即可使用本 skill。

## 配置

在 OpenClaw 的 **Secrets** 中配置后端地址（可选）：

- **`POKIETICKER_BASE_URL`**：PokieTicker API 根地址，例如 `http://localhost:8000` 或 `https://your-server.com`。不配置时默认使用 `http://localhost:8000`。

## 支持的 action

| action | 说明 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `list_tickers` | 列出所有跟踪标的 | — | — |
| `search_tickers` | 模糊搜索标的 | `q` | — |
| `ohlc` | 获取 OHLC 数据 | `symbol` | `start`, `end` (YYYY-MM-DD) |
| `news` | 某标的新闻（可按日过滤） | `symbol` | `date` (YYYY-MM-DD) |
| `news_range` | 日期区间内新闻 | `symbol`, `start`, `end` | — |
| `news_categories` | 新闻主题分类 | `symbol` | — |
| `forecast` | 基于近期新闻的预测 | `symbol` | `window` (3–60，默认 7) |
| `prediction` | 方向预测 | `symbol` | `horizon` (t1 / t5) |
| `backtest` | 回测结果 | `symbol` | `horizon` (t1 / t5) |
| `similar_days` | 历史相似交易日 | `symbol`, `date` | `top_k` (1–30，默认 10) |
| `story` | 生成标的价格故事（AI） | `symbol` | — |
| `range_local` | 区间内涨跌驱动（本地数据） | `symbol`, `start_date`, `end_date` | `question` |
| **数据更新** | | | |
| `update_data` | 全量/增量更新所有标的（OHLC+新闻、对齐、Layer0） | — | `full`（true=全量，默认 false=增量） |
| `fetch_data` | 拉取单标的 Polygon 数据（后台任务） | `symbol` | `start`, `end` (YYYY-MM-DD) |
| `process_data` | 单标的 Layer0 + Layer1 情感分析 | `symbol` | `batch_size`（默认 1000） |
| `submit_layer1` | 提交 Layer1 到 Anthropic Batch API（按待处理文章数取 top N 标的） | — | `top`（1–200，默认 50） |
| `batch_status` | 查询/收取 Batch 任务状态与结果 | `batch_id` | — |

调用结果统一为 `{ ok: true, data: ... }` 或 `{ ok: false, error: "..." }`，`data` 为后端 JSON 响应。
