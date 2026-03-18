# PokieTicker OpenClaw Skill 使用示例

在 OpenClaw 中调试或使用 **pokieticker** skill 时，可参考下列提问示例。建议先说「用 pokieticker」或「调用 pokieticker」，以便 OpenClaw 选用该 skill。调试时先确保 PokieTicker 后端已启动（`uv run uvicorn server.api.main:app --reload`）。

若出现「pokieticker not found」、Agent 尝试 `pip install pokieticker` 或报 `missing_brave_api_key` 等，请直接看文末 **四、OpenClaw 常见问题与排查**。

---

## 一、查询类（只读）

适合先用来验证 skill 与后端连通性，无副作用。

### list_tickers — 列出所有跟踪标的

- 用 pokieticker 列出所有跟踪的股票。
- 调用 pokieticker 看一下当前有哪些标的。
- pokieticker 里跟踪了哪些股票？

### search_tickers — 模糊搜索标的

- 用 pokieticker 搜索一下苹果。
- pokieticker 搜 AAPL。
- 在 pokieticker 里搜特斯拉 / TSLA。
- 用 pokieticker 查一下带「科技」的标的。

### ohlc — 获取 K 线 / OHLC 数据

- 用 pokieticker 查一下 AAPL 的 K 线。
- pokieticker 给我 AAPL 最近一段时间的 OHLC。
- 用 pokieticker 查 AAPL 从 2024-01-01 到 2024-03-01 的行情。

### news — 某标的新闻（可按日过滤）

- 用 pokieticker 看 AAPL 的新闻。
- pokieticker 查一下 TSLA 在 2024-03-01 那天的新闻。

### news_range — 日期区间内新闻

- 用 pokieticker 查 AAPL 在 2024-02-01 到 2024-02-29 之间的新闻。
- pokieticker 给我 MSFT 这段时间的新闻：start 2024-01-01，end 2024-01-31。

### news_categories — 新闻主题分类

- pokieticker 里 AAPL 的新闻分类 / 主题有哪些？
- 用 pokieticker 看 TSLA 的新闻按主题怎么分的。

### forecast — 基于近期新闻的预测

- 用 pokieticker 查 AAPL 的预测 / forecast。
- pokieticker 给我 AAPL 基于最近 30 天新闻的预测（window 30）。

### prediction — 方向预测

- pokieticker 里 AAPL 的方向预测是多少？
- 用 pokieticker 查 AAPL 的 T+5 预测（horizon t5）。

### backtest — 回测结果

- 用 pokieticker 看 AAPL 的回测结果。
- pokieticker 查一下 AAPL 的 t5 回测。

### similar_days — 历史相似交易日

- 用 pokieticker 查 2024-03-01 和 AAPL 历史上相似的交易日。
- pokieticker 找和 AAPL 在 2024-02-15 那天最像的 20 个历史日期（top_k 20）。

### story — 生成标的价格故事（AI）

- 用 pokieticker 给 AAPL 生成一段价格故事。
- pokieticker 用 AI 讲一下 TSLA 的走势和新闻关系。

### range_local — 区间内涨跌驱动（本地数据）

- 用 pokieticker 分析 AAPL 在 2024-02-01 到 2024-02-29 这段为什么涨/跌。
- pokieticker 用本地数据解释一下 MSFT 在这段时间的驱动：start_date 2024-01-01，end_date 2024-01-31。

---

## 二、数据更新类

会触发后端拉取、处理或提交任务，建议在查询类调试通过后再用。

### update_data — 全量 / 增量更新所有标的

- 用 pokieticker 做一次增量更新。（等价于 `./update_data.sh`）
- 用 pokieticker 做全量数据更新。（等价于 `./update_data.sh --full`）
- 调用 pokieticker 的 update_data，full 设为 true，全量拉一遍。

### fetch_data — 拉取单标的 Polygon 数据（后台）

- 用 pokieticker 拉取 TSLA 的数据。
- 调用 pokieticker 的 fetch_data，symbol 填 AAPL。
- pokieticker 拉一下 NVDA 从 2024-01-01 到 2024-03-01 的数据（start、end）。

### process_data — 单标的 Layer0 + Layer1 情感分析

- 用 pokieticker 对 AAPL 跑一下 process / 情感分析。
- 调用 pokieticker 的 process_data，symbol 填 TSLA，batch_size 500。

### submit_layer1 — 提交 Layer1 到 Anthropic Batch API

- 用 pokieticker 提交 Layer1 batch，top 10 个标的。
- 调用 pokieticker 的 submit_layer1，top 设为 50。
- pokieticker 把待处理文章最多的 20 个标的提交到 Layer1 Batch。

### batch_status — 查询 / 收取 Batch 任务

- 用 pokieticker 查一下 batch 状态，batch_id 是 xxx。（把 xxx 换成 submit_layer1 返回的 id）
- 调用 pokieticker 的 batch_status，batch_id 填刚才返回的那个。

---

## 三、调试建议

1. **先测只读**：先试「用 pokieticker 列出所有跟踪的股票」或「pokieticker 搜 AAPL」，确认返回正常再试更新类。
2. **看返回结构**：Skill 统一返回 `{ ok: true, data: ... }` 或 `{ ok: false, error: "..." }`，可根据 `ok` 和 `error` 判断是参数问题还是后端/网络问题。
3. **后端与 Secrets**：后端需在运行且可访问；若不在本机 8000，在 OpenClaw 的 Secrets 中配置 `POKIETICKER_BASE_URL`。
4. **更新类耗时**：`update_data`、`fetch_data`、`process_data`、`submit_layer1` 可能较慢或异步，接口会先返回，具体进度看服务端日志。

---

## 四、OpenClaw 常见问题与排查

调试时若出现下列现象，可对照处理。

### 0. 先确认：OpenClaw 是否找到了这个 skill？

若 Agent 一直把「pokieticker」当命令或去网上搜，很可能是 **OpenClaw 根本没有加载到这个 skill**。按下面步骤自检：

1. **看 skill 目录是否存在**  
   在终端执行：  
   `ls -la ~/.openclaw/skills/pokieticker`  
   应能看到该目录（或指向本仓库 `skills/pokieticker` 的符号链接），且其中有 `manifest.json` 和 `index.mjs`。若没有，需先按 [skills/pokieticker/README.md](../skills/pokieticker/README.md) 安装/链接到 `~/.openclaw/skills/pokieticker`。

2. **看 OpenClaw 是否扫描了 skills 目录**  
   打开 `~/.openclaw/openclaw.json`，确认是否有 `skills.load` 配置。若你用了 **extraDirs**，要写的是「包含各 skill 子目录」的那一层，例如本仓库应填 `"/path/to/PokieTicker/skills"`，这样 OpenClaw 才能看到其下的 `pokieticker` 目录。若没有配置 extraDirs，则只认 **默认的 `~/.openclaw/skills`**，所以必须把 skill 放在 `~/.openclaw/skills/pokieticker`。

3. **是否禁用了该 skill**  
   在 `openclaw.json` 的 `skills.entries` 里，若存在 `"pokieticker": { "enabled": false }`，会禁用该 skill。可删掉该项或改为 `true`。

4. **必须有 SKILL.md，本机 skill 才会被列出**  
   OpenClaw 只会把「含有 `SKILL.md`」的目录当作已安装的 skill 并展示给 Agent。本仓库的 pokieticker 已包含 `SKILL.md`（YAML 头 + 说明），放在 `~/.openclaw/skills/pokieticker` 后应能被识别。若你看到的是「You can use skillhub install [skill]」加一长串**可安装**的 skill（xquik、wechat-tool 等），那是 **skillhub 远程仓库列表**，不是「本机已加载的 skill」。要确认本机 skill，请重启/重载后问「列出我**已安装**的 skills」或「我本机有哪些 skills」，或在终端执行：`openclaw skills list --eligible`。

5. **重启或重载**  
   添加/修改 skill 后，**完全退出并重新打开 OpenClaw**（或在其设置里执行「重新加载 skills」），再在新对话里问「我有哪些已安装的 skills？」看返回里是否包含 pokieticker。

### 1. `pokieticker not found` / 命令退出码 1

**原因**：Agent 把「pokieticker」当成**系统命令**（在终端里执行 `pokieticker`），而不是 OpenClaw 的 **skill**。  
pokieticker 不是可执行命令，也不是 pip 包或 brew 公式，而是安装在 `~/.openclaw/skills/pokieticker` 下的 skill，必须由 OpenClaw 在对话中**调用 skill 接口**才会执行。

**排查与处理**：

- 确认 skill 已安装：`ls -la ~/.openclaw/skills/pokieticker`，应看到指向本仓库 `skills/pokieticker` 的符号链接或目录，且内含 `manifest.json`、`index.mjs`。
- 重启 OpenClaw 或在其设置中「重新加载 skills」，确保加载了 pokieticker。
- 在对话里**明确说明用 skill**，例如：「请用 OpenClaw 的 **pokieticker skill** 查 AAPL 在 2024-03-01 的历史相似交易日」，或先问「我当前有哪些可用的 skills？」确认 agent 能看到 pokieticker 再提问。
- 若 OpenClaw 有「选择工具/skill」的 UI，可主动选择 pokieticker 再发问。

### 2. `missing_brave_api_key` / web_search (brave) needs a Brave Search API key

**原因**：与 pokieticker 无关。Agent 在尝试使用 **网页搜索**（Brave Search）时，发现未配置 API Key。

**处理**：

- 若不需要网页搜索：可忽略；让 agent 改用 pokieticker skill 而不是 web search。
- 若需要网页搜索：运行 `openclaw configure --section web` 按提示配置，或在 Gateway 环境中设置 `BRAVE_API_KEY`。详见 [OpenClaw web 工具文档](https://docs.openclaw.ai/tools/web)。

### 3. Agent 执行 `pip install pokieticker` 或 `brew install pokieticker`

**原因**：Agent 误以为「pokieticker」是一个要**安装**的 Python 包或系统软件，没有识别为已安装的 **OpenClaw skill**。

**说明**：pokieticker 不发布在 PyPI，也没有 Homebrew 公式。它是本仓库提供的 OpenClaw skill，通过「安装到 `~/.openclaw/skills/pokieticker`」即可使用，无需 pip/brew。

**处理**：同「1. pokieticker not found」——确认 skill 目录存在且被 OpenClaw 加载，并在提问时明确说「用 **pokieticker 这个 skill**」或先列出 skills 再指定使用 pokieticker。

### 4. `pip` / `externally-managed-environment` 等 Python 环境报错

**原因**：Agent 误用了系统 Python 或错误地尝试安装「pokieticker 包」，触发了 PEP 668 等环境限制。同样与「pokieticker 是 skill、不是 pip 包」有关。

**处理**：不要让 agent 对「pokieticker」执行 pip/brew；引导其使用 OpenClaw 的 pokieticker skill 调用后端 API 即可。PokieTicker 后端需在项目目录用 `uv run uvicorn ...` 单独启动，与 OpenClaw 的 Python 环境无关。

### 5. Agent 用 web_fetch 去搜 GitHub / 网页找「pokieticker」

**原因**：Agent 不知道本地已有 pokieticker skill，于是用网页搜索去找「pokieticker」是什么、怎么用。

**处理**：在对话开头说明「我本地已经安装了 OpenClaw 的 pokieticker skill，请直接调用这个 skill，不要用网页搜索」。并确认 `~/.openclaw/skills/pokieticker` 存在且已被加载。

### 6. 问「用 pokieticker 查…」却只看到「You can use skillhub install」和一串可安装的 skill（xquik、wechat-tool 等），没有 pokieticker

**原因**：Agent 去 **skillhub 远程仓库**里找「pokieticker」，找到的是「可安装」列表，不是「本机已安装」的 skill。本机放在 `~/.openclaw/skills/pokieticker` 的 skill 只有在目录里包含 **SKILL.md** 时才会被 OpenClaw 当作已安装 skill 并列入可用列表。

**处理**：

- 确认目录内有 **SKILL.md**（本仓库已提供，含 name、description 和简要说明）。若没有，从仓库复制或拉取最新 `skills/pokieticker/SKILL.md` 到 `~/.openclaw/skills/pokieticker/`。
- 完全重启 OpenClaw（或重新加载 skills），在新对话里先问「列出我**已安装**的 skills」或「我本机有哪些 skills」，确认列表里出现 pokieticker 后再问「用 pokieticker 查 2024-03-01 和 AAPL 历史上相似的交易日」。
- 终端可执行：`openclaw skills list --eligible`，检查 pokieticker 是否在「当前环境可用」的列表中。

---

**小结**：pokieticker 是 **OpenClaw skill**（装在 `~/.openclaw/skills/pokieticker`），不是系统命令、不是 pip 包、不是 brew 包。若 Agent 始终不调用它，**先做上面第 0 步**确认 OpenClaw 是否真的加载到了该 skill；再在提问时明确说「用 pokieticker skill」调用。
