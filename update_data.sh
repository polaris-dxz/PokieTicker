#!/usr/bin/env bash
# PokieTicker 数据更新脚本 — 拉取最新 OHLC + 新闻，可选跑 Layer 1 情感分析
# 用法: ./update_data.sh [--full] [--layer1] [--no-git]
#   --full    全量拉取 (bulk_fetch)，默认是增量 (weekly_update)
#   --layer1  更新完成后提交 Layer 1 Batch，并提示如何执行 batch_collect
#   --no-git  成功更新后仍打包 .data/pokieticker.db.gz，但不 git commit / push（适合 cron）

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

# 检查 .data 和 DB
[[ -f "$DB_PATH" ]] || err "未找到 $DB_PATH，请先运行 ./install.sh 完成安装与数据库准备。"

# 可选参数
DO_FULL=false
DO_LAYER1=false
DO_GIT=true
for arg in "$@"; do
  [[ "$arg" == "--full" ]]    && DO_FULL=true
  [[ "$arg" == "--layer1" ]]  && DO_LAYER1=true
  [[ "$arg" == "--no-git" ]]  && DO_GIT=false
done

DB_PATH=".data/pokieticker.db"
DB_GZ_PATH=".data/pokieticker.db.gz"

# 检查 Polygon API Key（拉数据必需）
if ! grep -q "POLYGON_API_KEY=.\+" .env 2>/dev/null && [[ -z "$POLYGON_API_KEY" ]]; then
  warn "未检测到 POLYGON_API_KEY（.env 或环境变量）。拉取 OHLC/新闻将失败。"
  read -p "仍要继续？ [y/N] " -n 1 -r; echo
  [[ $REPLY =~ ^[yY]$ ]] || exit 1
fi

# Step 1: 拉取数据
if [[ "$DO_FULL" == true ]]; then
  info "全量拉取 (bulk_fetch)..."
  uv run python -m server.bulk_fetch
else
  info "增量更新 (weekly_update)..."
  uv run python -m server.weekly_update
fi

# Step 2: 可选提交 Layer 1 Batch
if [[ "$DO_LAYER1" == true ]]; then
  if ! grep -q "ANTHROPIC_API_KEY=.\+" .env 2>/dev/null && [[ -z "$ANTHROPIC_API_KEY" ]]; then
    warn "未设置 ANTHROPIC_API_KEY，跳过 Layer 1。需要情感分析时请在 .env 中配置后重新运行并加 --layer1"
  else
    info "提交 Layer 1 Batch (batch_submit --top 50)..."
    BATCH_OUT=$(uv run python -m server.batch_submit --top 50 2>&1) || true
    echo "$BATCH_OUT"
    BATCH_ID=$(echo "$BATCH_OUT" | sed -n 's/.*Batch submitted! ID: \([^[:space:]]*\).*/\1/p')
    if [[ -n "$BATCH_ID" ]]; then
      echo ""
      info "Batch 已提交。等 Anthropic 处理完成后执行："
      echo "  uv run python -m server.batch_collect $BATCH_ID"
      echo ""
    fi
  fi
else
  echo ""
  info "如需对新新闻做情感分析 (Layer 1)，请执行："
  echo "  ./update_data.sh --layer1   # 仅提交 Batch（在本次增量之后）"
  echo "  或  ./update_data.sh --full --layer1   # 全量 + 提交 Batch"
  echo "  然后根据终端输出的 batch_id 执行： uv run python -m server.batch_collect <batch_id>"
  echo ""
fi

# Step 3: 打包 DB → .data/pokieticker.db.gz（与 .gitignore 中 !.data/pokieticker.db.gz 对应，便于提交）
info "打包数据库 → $DB_GZ_PATH ..."
if ! command -v gzip >/dev/null 2>&1; then
  err "未找到 gzip 命令，无法打包数据库。"
fi
# -k 保留源文件；-f 覆盖已有 .gz
gzip -kf "$DB_PATH"
[[ -f "$DB_GZ_PATH" ]] || err "打包失败：未生成 $DB_GZ_PATH"

# Step 4: 可选提交并推送到远程
if [[ "$DO_GIT" == true ]]; then
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    warn "当前目录不在 Git 仓库内，已跳过 commit/push（$DB_GZ_PATH 已生成）。"
  else
    info "提交 $DB_GZ_PATH 到 Git ..."
    git add -- "$DB_GZ_PATH"
    if git diff --staged --quiet; then
      info "Git 无变更（与上次提交的压缩包相同），跳过 commit/push。"
    else
      MSG="chore(data): refresh pokieticker.db.gz ($(date +%Y-%m-%d))"
      git commit -m "$MSG"
      if git push; then
        info "已推送到远程仓库。"
      else
        warn "git push 失败，请检查网络、分支 upstream 与凭证；本地 commit 已保留。"
      fi
    fi
  fi
else
  info "已使用 --no-git，跳过 git commit/push。"
fi

info "数据更新脚本执行完成。"
