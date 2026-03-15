#!/usr/bin/env bash
# PokieTicker 安装脚本 — 使用 uv (Python) + pnpm (前端)
# 用法: ./install.sh [--start]
#   --start  安装完成后启动前后端服务

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

# 检查命令
command -v uv   >/dev/null 2>&1 || err "请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/"
command -v pnpm >/dev/null 2>&1 || err "请先安装 pnpm: npm install -g pnpm"

START_AFTER=false
for arg in "$@"; do
  [[ "$arg" == "--start" ]] && START_AFTER=true
done

# --- Python 后端 (uv) ---
info "创建 Python 虚拟环境 (.venv) ..."
uv venv

info "安装 Python 依赖 (requirements.txt) ..."
uv pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# --- 数据库 ---
if [[ ! -f pokieticker.db && -f pokieticker.db.gz ]]; then
  info "解压预置数据库 pokieticker.db.gz ..."
  gunzip -k pokieticker.db.gz
elif [[ ! -f pokieticker.db ]]; then
  warn "未找到 pokieticker.db 或 pokieticker.db.gz，部分功能可能不可用。"
fi

# --- 前端 (pnpm) ---
info "安装前端依赖 (pnpm) ..."
(cd frontend && pnpm install)

info "安装完成。"

if [[ "$START_AFTER" == true ]]; then
  info "正在启动后端与前端..."
  # 后台启动 uvicorn，退出时清理
  uv run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000 &
  UV_PID=$!
  trap "kill $UV_PID 2>/dev/null; exit" EXIT INT TERM

  # 等待后端 /api/health 就绪（最多 30 秒）
  info "等待后端就绪 (http://127.0.0.1:8000) ..."
  for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health 2>/dev/null | grep -q 200; then
      info "后端已就绪。"
      break
    fi
    if ! kill -0 $UV_PID 2>/dev/null; then
      err "后端启动失败，请检查上方错误信息。"
    fi
    sleep 1
  done
  if ! curl -s -o /dev/null http://127.0.0.1:8000/api/health 2>/dev/null; then
    err "后端 30 秒内未就绪，请单独运行: uv run uvicorn backend.api.main:app --reload"
  fi

  (cd frontend && pnpm run dev)
else
  echo ""
  echo "启动方式（开两个终端）："
  echo "  终端 1 (后端):  uv run uvicorn backend.api.main:app --reload"
  echo "  终端 2 (前端):  cd frontend && pnpm run dev"
  echo ""
  echo "或一键启动:  ./install.sh --start"
  echo "然后打开:    http://localhost:7777/PokieTicker/"
fi
