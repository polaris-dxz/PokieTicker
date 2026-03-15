# PokieTicker 原理与流程

本文档说明项目的设计思路、数据流水线、ML 流程以及端到端使用流程。

---

## 一、项目目标与原理

### 1.1 要解决什么问题

- 作为股民，看 K 线时经常不知道**为什么涨、为什么跌**，新闻分散、信息碎片化。
- PokieTicker 的目标是建立**事件驱动思维**：把「价格变动」和「当日/近期新闻」绑在一起，用 AI 做情感与归因，用 ML 做短期方向预测与历史相似日匹配。

### 1.2 核心思路

1. **新闻上盘面**：每个交易日对应一根 K 线，上面打点表示当天有新闻，点击可看标题与情感。
2. **分层处理新闻**：先规则过滤（Layer 0）→ 再批量情感分析（Layer 1，Haiku）→ 点击单篇时再做深度分析（Layer 2，Sonnet），控制成本。
3. **新闻与交易日对齐**：按 `published_utc` 映射到最近交易日，并计算 T+0/1/3/5/10 收益率，供特征与回测使用。
4. **预测与相似日**：用「新闻情感 + 技术指标」组成 31 维特征，训练 XGBoost（T+1/T+5）；预测时再按滑动窗口做余弦相似度，找出历史上新闻模式相似的区间，看后续涨跌。

---

## 二、整体架构

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                     Frontend (React + Vite + D3.js)      │
                    │  CandlestickChart │ NewsPanel │ PredictionPanel │ ...   │
                    └─────────────────────────────┬───────────────────────────┘
                                                  │ HTTP (proxy to :8000)
                    ┌─────────────────────────────▼───────────────────────────┐
                    │                  Backend (FastAPI + SQLite)               │
                    │  /api/stocks  /api/news  /api/analysis  /api/predict     │
                    └─────────────────────────────┬───────────────────────────┘
                                                  │
                    ┌─────────────────────────────▼───────────────────────────┐
                    │                  pokieticker.db (SQLite, WAL)             │
                    │  tickers, ohlc, news_raw, news_ticker, layer0/1/2,       │
                    │  news_aligned, batch_jobs, batch_request_map             │
                    └──────────────────────────────────────────────────────────┘
```

- **前端**：选股 → 看 K 线 + 新闻点 → 看情感/分类/预测/相似日/区间问答。
- **后端**：读库、跑推理、调 Anthropic；不直接调 Polygon（数据由离线脚本拉取）。

---

## 三、数据流水线（从原始数据到可用的「新闻+情感」）

整体顺序：**Polygon 拉取 → 新闻-交易日对齐 → Layer 0 → Layer 1（可选 Batch）→ Layer 2（按需）**。

### 3.1 数据获取（Polygon）

| 脚本/模块 | 作用 |
|----------|------|
| `bulk_fetch.py` | 批量拉取多标的 OHLC + 新闻，写入 `ohlc`、`news_raw`、`news_ticker`；拉完后对每个 symbol 跑 `align_news_for_symbol`、`run_layer0`。 |
| `weekly_update.py` | 增量：只拉取上次更新之后的 OHLC 与新闻，同样做对齐与 Layer 0。 |
| `polygon/client.py` | 封装 Polygon REST（OHLC、新闻列表、ticker 信息），带重试与限速（免费档 5 req/min）。 |

数据落表：

- **tickers**：symbol、name、sector、last_ohlc_fetch、last_news_fetch。
- **ohlc**：symbol, date, open, high, low, close, volume, ...
- **news_raw**：id, title, description, publisher, published_utc, article_url, tickers_json, ...
- **news_ticker**：news_id, symbol（多对多）。

### 3.2 新闻与交易日对齐（alignment）

- **目的**：把每条新闻的发布时间映射到一个「交易日」，并计算该交易日当天及之后 1/3/5/10 日的收益率，供 Layer 1 展示、特征工程和回测使用。
- **逻辑**：`pipeline/alignment.py` 的 `align_news_for_symbol(symbol)`：
  - 用 `ohlc` 的日期序列得到「交易日列表」；
  - 对尚未对齐的新闻，用 `published_utc` 转为日期，再映射到**最近的一个交易日**（可理解为「这条新闻在盘面上算到哪一天」）；
  - 计算该交易日的 ret_t0（当日涨跌）、ret_t1/t3/t5/t10（之后 1/3/5/10 日相对当日的收益率）。
- **落表**：`news_aligned(news_id, symbol, trade_date, published_utc, ret_t0, ret_t1, ret_t3, ret_t5, ret_t10)`。

这样，前端「某日新闻 + T+1/T+5 收益」、以及 ML 的 target（未来 N 日涨跌）都来自同一套对齐结果。

### 3.3 Layer 0：规则过滤（零成本）

- **目的**：在调用 LLM 前先过滤掉明显无关或低质内容，节省 Layer 1 的 token。
- **实现**：`pipeline/layer0.py`。规则包括：描述为空、过短、多标的综述（>10 个 ticker 且目标不在标题）、列表式标题（如 "Top 10 …"）等。
- **落表**：`layer0_results(news_id, symbol, passed, reason)`，只对 `passed=1` 的新闻进入 Layer 1。

### 3.4 Layer 1：批量情感与归因（Claude Haiku）

- **目的**：对通过 Layer 0 的新闻，批量打上「是否相关、情感、简要讨论、看涨/看跌理由」。
- **实现**：
  - **同步**：`layer1.py` 的 `process_batch_group(symbol, articles)`，每批最多 50 篇，一次 `messages.create`，返回紧凑 JSON（r/s/e/u/d 等）。
  - **异步**：`batch_submit.py` 按 top N 标的收集待处理文章，按 50 篇/请求打成 Batch API 请求；`batch_collect.py` 拉取 Batch 结果并写回 DB。
- **落表**：`layer1_results(news_id, symbol, relevance, key_discussion, chinese_summary, sentiment, reason_growth, reason_decrease, ...)`。
- **Batch 元数据**：`batch_jobs`、`batch_request_map` 记录 batch_id、custom_id、symbol、article_ids，供 collect 时解析。

### 3.5 Layer 2：按需深度分析（Claude Sonnet）

- **目的**：用户点击某条新闻时，再做一次深度解读（讨论、看涨/看跌理由展开），并缓存，避免重复调用。
- **实现**：`pipeline/layer2.py` 的 `analyze_article(news_id, symbol)`：先查 `layer2_results`，命中则直接返回；否则调 Sonnet，写回再返回。
- **其他**：同一模块内还有 `analyze_range`（区间「为什么涨/跌」）和 `generate_story`（根据 OHLC+新闻生成故事），均用 Sonnet、按需调用。
- **落表**：`layer2_results(news_id, symbol, discussion, growth_reasons, decrease_reasons, created_at)`。

### 3.6 数据流小结

```
Polygon API
    │
    ▼
ohlc + news_raw + news_ticker
    │
    ▼
alignment → news_aligned (trade_date, ret_t0..t10)
    │
    ▼
layer0 → layer0_results (passed=1 的才进入下一层)
    │
    ▼
layer1 (Haiku 同步/或 Batch) → layer1_results (relevance, sentiment, reason_*)
    │
    ▼
layer2 (Sonnet，点击时) → layer2_results (discussion, growth/decrease_reasons)
```

---

## 四、ML 流程：特征、训练、推理与预测

### 4.1 特征工程（31 维）

- **单位**：**每个 (symbol, trade_date) 一行**，即「每个标的的每个交易日」一条样本。
- **数据来源**：
  - **新闻侧**：`news_aligned` + `layer1_results` 按 `trade_date` 聚合 → 当日文章数、正/负/中性数、相关数、情感分、正负比例等；再做 3/5/10 日滚动均值与情感动量等（见 `ml/features.py` 的 `_load_news_features` 与滚动列）。
  - **价格侧**：`ohlc` 的 open/high/low/close/volume → 收益率(1/3/5/10d)、波动率、量比、缺口、均线比、RSI、星期等；**全部用 shift(1) 或过去窗口**，避免未来信息泄露。
- **目标**：`target_t1/t3/t5` = 未来 1/3/5 日收盘价是否高于当前收盘（二分类 0/1），用于训练和评估。
- **FEATURE_COLS**：共 31 个（新闻相关 + 滚动新闻 + 价格/技术），见 `features.py` 的 `FEATURE_COLS`。

### 4.2 训练

- **入口**：`python -m backend.ml.train [--symbol SYM] [--backtest] [--lstm]`（`ml/train.py`）。
- **逻辑**：对每个 symbol（或全库），对 horizon `t1`、`t5` 各训练一个 XGBoost 二分类模型；时间序列划分（如 80% 训练 / 20% 测试），评估 accuracy、baseline、precision/recall/F1；可选跑 backtest、可选训练 LSTM（部分标的）。
- **输出**：`backend/ml/models/{SYMBOL}_t1.joblib`、`{SYMBOL}_t1_meta.json`（及 t5、部分 LSTM）。没有这些文件时，预测接口会返回 404（见下文）。

### 4.3 推理与预测接口

- **入口 API**：`GET /api/predict/{symbol}/forecast?window=7|30`（`routers/predict.py` → `ml/inference.py` 的 `generate_forecast`）。
- **流程概要**：
  1. **特征**：`build_features(symbol)` 得到该标的到最近交易日为止的特征表；若为空则返回 404（无特征数据）。
  2. **近期新闻汇总**：按 `window`（7 或 30 天）取最近一段时间的 `news_aligned` + Layer1，做情感统计、头条、高影响文章列表。
  3. **窗口特征向量**：对最近 `window` 个交易日的特征做平均，得到一个向量，用于相似日匹配。
  4. **模型预测**：若存在 `{symbol}_t1.joblib` / `t5.joblib`（及可选 LSTM），则用当前最新一行的 FEATURE_COLS 做预测，得到方向与置信度；若**一个模型都没有**，则返回 404（无训练模型）。
  5. **相似历史区间**：用当前窗口的平均特征向量，在历史滑动窗口上做余弦相似度，取 top-K 相似区间，并统计这些区间之后 5/10 日的收益分布。
  6. **结论文案**：根据新闻汇总、模型预测、相似区间统计拼一段英文结论（无额外 API 调用）。
- **返回**：JSON 含 `news_summary`、`prediction`（t1/t5 等）、`similar_periods`、`similar_stats`、`conclusion` 等。若中间任一步失败（无特征/无模型），则返回 `error`，路由层转为 404。

因此，**预测 404 = 该标的没有训练好的模型**，需要先执行 `python -m backend.ml.train --symbol AAPL`（或全量 train）。

### 4.4 ML 流程小结

```
news_aligned + layer1_results + ohlc
    │
    ▼
build_features(symbol) → 每交易日一行，31 维 FEATURE_COLS + target_t1/t5
    │
    ├── 训练：train(symbol, horizon) → XGBoost → .joblib + _meta.json
    │
    └── 预测：generate_forecast(symbol, window)
              ├── 近期新闻汇总
              ├── 窗口特征向量 → 相似日（余弦相似度）
              ├── 加载 .joblib 做 t1/t5 预测
              └── 拼 conclusion → 返回前端
```

---

## 五、用户使用流程（从前端到后端）

1. **选股**：前端请求 `GET /api/stocks`、`/api/stocks/{sym}/ohlc`，展示 K 线（D3 蜡烛图）。
2. **看新闻点**：按日期从 `GET /api/news/{sym}?date=...` 或类似接口取该日新闻，在 K 线上打点；点击某日可锁定右侧面板为该日新闻列表。
3. **看情感与分类**：新闻列表和分类来自 `layer1_results`（及 categories 等）；点击单条可能触发 `POST /api/analysis/deep` 等，后端查/写 `layer2_results`。
4. **看预测**：前端请求 `GET /api/predict/{sym}/forecast?window=7` 和 `?window=30`；若该标的未训练模型则 404，前端可提示「暂无预测」或引导先训练。
5. **区间问答**：用户选择日期区间并提问「为什么跌/涨」，前端调 `analyze_range` 对应 API，后端用 Sonnet 结合该区间 OHLC + 新闻返回结构化分析。

整体上，**所有「为什么」和「预测」都依赖：对齐好的新闻（news_aligned）、Layer 1 情感（layer1_results）、以及（对预测而言）训练好的 XGBoost 模型文件**。

---

## 六、关键表与依赖关系（简表）

| 表名 | 主要用途 |
|------|----------|
| tickers | 标的列表与最后拉取时间 |
| ohlc | 日线 OHLCV，对齐与特征的日期基准 |
| news_raw | 原始新闻元数据 |
| news_ticker | 新闻–标的多对多 |
| news_aligned | 新闻→交易日 + ret_t0..t10，特征与展示的桥梁 |
| layer0_results | 规则过滤结果，passed=1 进 Layer 1 |
| layer1_results | 情感、相关性与涨跌理由，前端列表与 31 维特征中的新闻部分 |
| layer2_results | 单篇深度分析缓存 |
| batch_jobs / batch_request_map | Batch API 提交与结果回收 |

---

## 七、文档与代码对应

| 概念 | 代码位置 |
|------|----------|
| 数据获取与对齐 | `bulk_fetch.py`, `weekly_update.py`, `pipeline/alignment.py` |
| Layer 0/1/2 | `pipeline/layer0.py`, `layer1.py`, `layer2.py` |
| Batch 提交与收集 | `batch_submit.py`, `batch_collect.py` |
| 特征与目标 | `ml/features.py`（FEATURE_COLS, build_features, target_t*） |
| 训练 | `ml/train.py`, `ml/model.py` |
| 预测与相似日 | `ml/inference.py`（generate_forecast, _find_similar_periods） |
| 预测 API | `api/routers/predict.py`（get_forecast → 404 当无模型/无特征） |

以上即 PokieTicker 的原理与端到端流程说明；实现细节以代码为准，本文档作整体导航与设计参考。
