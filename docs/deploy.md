# PokieTicker 免费部署指南

本指南介绍如何**零月费**把 PokieTicker 部署到公网，用一台服务同时提供前端页面和 API。

---

## 一、部署思路

- **前后端合一**：构建后的前端（`frontend/dist`）由 FastAPI 托管，访问根路径会重定向到 `/PokieTicker/`，API 在 `/api/*`。
- **数据库**：使用项目自带的 SQLite（`pokieticker.db`）。若仓库里有 `pokieticker.db.gz`，在构建阶段解压即可；若无，需自行准备或接受「无数据」仅演示界面。
- **免费额度**：下面以 [Render](https://render.com) 为例（免费 Web Service 有冷启动、每月 750 小时）。也可用 [Fly.io](https://fly.io) 等，流程类似。

---

## 二、Render 部署（推荐）

### 2.1 前置条件

- 代码在 **GitHub** 上。
- 若需预置数据：仓库内包含 `pokieticker.db.gz`（或构建时能生成/下载到 `pokieticker.db`）。

### 2.2 在 Render 创建 Web Service

1. 登录 [Render](https://render.com) → **Dashboard** → **New** → **Web Service**。
2. 连接你的 GitHub 仓库（如 `owengetinfo-design/PokieTicker`）。
3. 配置如下：

| 配置项 | 值 |
|--------|-----|
| **Name** | 随意，如 `pokieticker` |
| **Region** | 选离你近的 |
| **Branch** | `main` 或你的默认分支 |
| **Runtime** | **Docker** 或 **Native**（二选一，见下） |

### 2.3 方案 A：Native 环境（不用 Docker）

**Build Command（构建命令）：**

```bash
pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
test -f pokieticker.db.gz && gunzip -k pokieticker.db.gz || true
```

（若项目用 pnpm：把 `npm ci` 换成 `pnpm install --frozen-lockfile`，`npm run build` 换成 `pnpm run build`。）

**Start Command（启动命令）：**

```bash
python run.py
```

或显式传端口：

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

- `run.py` 会读取环境变量 `PORT`（Render 会自动注入），默认 8000。

**Environment（环境变量，可选）：**

- 仅做只读演示可不填。
- 若要拉新数据或跑 AI：在 Render 的 **Environment** 里添加 `POLYGON_API_KEY`、`ANTHROPIC_API_KEY`（生产环境不要提交到 Git）。

### 2.4 方案 B：Docker 部署

在项目根目录新建 **Dockerfile**（见下节），Render 选 **Docker** 时会自动用该文件构建并运行。

### 2.5 部署后访问

- 若服务名为 `pokieticker` 且区域为 Oregon，地址一般为：  
  **https://pokieticker.onrender.com**
- 打开后会自动跳转到 **https://pokieticker.onrender.com/PokieTicker/**，即可使用。
- 健康检查：**https://pokieticker.onrender.com/api/health** 应返回 `{"status":"ok"}`。

### 2.6 免费额度说明

- 免费 Web Service 在约 15 分钟无访问后会**休眠**，下次访问需等待几十秒冷启动。
- 每月 750 小时，单实例够用。
- 磁盘不持久：每次重新部署会清空本地文件，数据库需来自构建（如解压 `pokieticker.db.gz`）或外部存储（需自行接 S3 等）。

---

## 三、Dockerfile 示例（可选）

若希望用 Docker 在 Render / 自建机 / 其他平台统一部署，可在项目根目录添加：

```dockerfile
# 阶段 1：构建前端
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json frontend/pnpm-lock.yaml* ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile || npm ci
COPY frontend/ ./
RUN pnpm run build || npm run build

# 阶段 2：运行
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist
COPY .env* ./
RUN test -f pokieticker.db.gz && gunzip -k pokieticker.db.gz || true

ENV PORT=8000
EXPOSE 8000
CMD uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}
```

- 构建时会把前端打进镜像，并解压 `pokieticker.db.gz`（若存在）。
- 运行时会读环境变量 `PORT`（Render 会设），未设则用 8000。

---

## 四、Fly.io 简要步骤（免费额度）

1. 安装 [flyctl](https://fly.io/docs/hands-on/install-flyctl/) 并登录。
2. 在项目根目录执行：  
   `fly launch`  
   按提示选 region、不绑定 PostgreSQL 等。
3. 在 **fly.toml** 中确保有：
   - `[env]` 中 `PORT = "8080"`（或 Fly 给你的端口）。
   - 启动命令用：`uvicorn backend.api.main:app --host 0.0.0.0 --port 8080`（与 PORT 一致）。
4. 构建与数据库：可用 Dockerfile（同上），或在 **Dockerfile** 里用多阶段构建，把 `frontend/dist` 和（可选）解压后的 `pokieticker.db` 打进镜像。
5. 部署：`fly deploy`。

Fly 免费机型的资源与流量有限制，但可长期运行、不因闲置而休眠。

---

## 五、自建 VPS（如 Oracle Cloud 免费机）

若你有 1 台免费 VPS（如 Oracle Cloud Always Free）：

1. 在服务器上 clone 仓库，安装 Python 3.10+、Node 18+（或使用 Docker）。
2. 构建：  
   `pip install -r requirements.txt`，`cd frontend && pnpm install && pnpm run build`，必要时 `gunzip -k pokieticker.db.gz`。
3. 使用环境变量 `PORT`（例如 8000），启动：  
   `uvicorn backend.api.main:app --host 0.0.0.0 --port 8000`  
   或用 systemd / supervisor 管理进程。
4. 用 Nginx/Caddy 做反向代理，绑域名并配 HTTPS（Let’s Encrypt 免费证书）。

---

## 六、常见问题

- **打开页面空白或 404**  
  确认构建产物在 `frontend/dist`，且后端已挂载静态资源（见 `backend/api/main.py` 中对 `frontend/dist` 的挂载）。访问路径应为 **/PokieTicker/**（带尾部斜杠）。

- **API 404 / 预测不可用**  
  预测接口依赖训练好的模型（见 [原理与流程](overview.md)）。免费部署通常不包含模型文件，需在本地跑 `python -m backend.ml.train` 后把 `backend/ml/models/` 打进镜像或部署包，或接受「暂无预测」的提示。

- **没有数据库**  
  若仓库没有 `pokieticker.db.gz`，可在构建命令里从 GitHub Release 或其它地址下载并解压，或部署一个「空库」仅演示前端（部分接口会无数据）。

按上述步骤即可在**零月费**的前提下把 PokieTicker 部署到公网；需要拉新数据或使用 AI 时，再在对应平台配置 API Key 即可。
