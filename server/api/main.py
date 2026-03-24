import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from server.config import PROJECT_ROOT, resolved_env_file_path, settings
from server.database import init_db
from server.api.routers import stocks, news, analysis, predict, pipeline

app = FastAPI(title="PokieTicker", version="1.0.0")

logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow same-origin when server serves frontend; restrict in production if needed
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(predict.router, prefix="/api/predict", tags=["predict"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])


@app.on_event("startup")
def startup():
    init_db()
    env_path = resolved_env_file_path()
    key = (settings.anthropic_api_key or "").strip()
    if key:
        logger.info(
            "PokieTicker: PROJECT_ROOT=%s env_file=%s exists=%s anthropic_base_url=%s key_len=%s key_tail=%s",
            PROJECT_ROOT,
            env_path,
            env_path.is_file(),
            (settings.anthropic_base_url or "").strip(),
            len(key),
            key[-4:] if len(key) >= 4 else "?",
        )
    else:
        logger.warning(
            "PokieTicker: ANTHROPIC_API_KEY 为空; 若已在 .env 中配置仍无效，请检查 shell 是否 export 了同名变量（会覆盖 .env）。"
            " PROJECT_ROOT=%s env_file=%s exists=%s",
            PROJECT_ROOT,
            env_path,
            env_path.is_file(),
        )


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Production: serve app static files (build output at app/dist, base path /PokieTicker/)
_app_dist = PROJECT_ROOT / "app" / "dist"
if _app_dist.exists():
    app.mount("/PokieTicker", StaticFiles(directory=str(_app_dist), html=True), name="app")

    @app.get("/")
    def _redirect_root():
        return RedirectResponse(url="/PokieTicker/", status_code=302)
