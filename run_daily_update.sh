#!/usr/bin/env bash
set -euo pipefail

EXT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK_DIR="/tmp/pokieticker_update.lock"
LOG_DIR="${HOME}/Library/Logs/pokieticker"

mkdir -p "$LOG_DIR"

TS="$(date '+%F %T')"
echo "[$TS] daily wrapper start" >> "$LOG_DIR/daily_update.log"

# 1-5=周一到周五，6-7=周六/周日
weekday="$(date +%u)"
if [[ "$weekday" -ge 6 ]]; then
  echo "[$TS] weekend (weekday=$weekday), skip" >> "$LOG_DIR/daily_update.log"
  exit 0
fi

# 防止重入：上一次还没跑完则跳过
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$TS] already running, skip" >> "$LOG_DIR/daily_update.log"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

cd "$EXT_DIR"

# 确保非交互：缺 POLYGON_API_KEY 时 update_data.sh 会 read -p 等输入
if ! grep -q '^POLYGON_API_KEY=.*' .env 2>/dev/null && [[ -z "${POLYGON_API_KEY:-}" ]]; then
  echo "[$TS] ERROR: POLYGON_API_KEY missing in .env or env var" >> "$LOG_DIR/daily_update.log"
  exit 1
fi

# launchd 环境 PATH 可能不包含 homebrew，需要补上 uv
export PATH="/opt/homebrew/bin:$PATH"

# 定时任务通常无交互、也未必配置 push 凭证；只更新数据并打包 .gz，不自动 git push
./update_data.sh --no-git >> "$LOG_DIR/daily_update_data.log" 2>&1

echo "[$(date '+%F %T')] daily wrapper done" >> "$LOG_DIR/daily_update.log"

