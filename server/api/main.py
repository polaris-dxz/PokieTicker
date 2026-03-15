from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from server.config import PROJECT_ROOT
from server.database import init_db
from server.api.routers import stocks, news, analysis, predict

app = FastAPI(title="PokieTicker", version="1.0.0")

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


@app.on_event("startup")
def startup():
    init_db()


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
