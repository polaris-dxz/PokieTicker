---
name: pokieticker
description: 查询或更新 PokieTicker 数据。当用户要查股票列表、K 线、新闻、分类、预测、历史相似交易日，或触发数据更新 / Layer1 提交时使用。触发词包括「用 pokieticker」「PokieTicker 查」「股票/标的/OHLC/新闻/预测/相似交易日/更新数据」。
version: 1.0.0
---

# PokieTicker Skill

当用户需要以下任一能力时，使用 **pokieticker** 这个 skill（工具）：

- 列出或搜索跟踪的股票（list_tickers, search_tickers）
- 查某只股票的 K 线 / OHLC（ohlc）、新闻（news、news_range、news_categories）
- 查预测或回测（forecast、prediction、backtest）、历史相似交易日（similar_days）
- 生成价格故事或区间涨跌驱动（story、range_local）
- 触发数据更新：增量/全量更新（update_data）、单标的拉取（fetch_data）、情感分析（process_data）、提交 Layer1 Batch（submit_layer1）、查 Batch 状态（batch_status）

调用时传入参数：`action`（必填，取上述能力之一），以及该 action 所需的 `symbol`、`date`、`start`、`end`、`window`、`full`、`batch_id` 等。后端默认地址为 `http://localhost:8000`，可在 OpenClaw Secrets 中配置 `POKIETICKER_BASE_URL`。

示例：查 AAPL 在 2024-03-01 的历史相似交易日 → action=similar_days, symbol=AAPL, date=2024-03-01。
