import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

from server.database import get_conn
from server.polygon.client import fetch_ohlc, fetch_news
from server.pipeline.layer0 import run_layer0
from server.pipeline.layer1 import get_pending_articles, run_layer1, check_batch_status, collect_batch_results
from server.pipeline.alignment import align_news_for_symbol

import json

router = APIRouter()


class FetchRequest(BaseModel):
    symbol: str
    start: Optional[str] = None
    end: Optional[str] = None


class ProcessRequest(BaseModel):
    symbol: str
    batch_size: int = 1000


class UpdateAllRequest(BaseModel):
    full: bool = False


class SubmitLayer1Request(BaseModel):
    top: int = 50


def _run_update_all(full: bool):
    """Run bulk_fetch (full) or weekly_update (incremental) in background."""
    try:
        if full:
            from server.bulk_fetch import main as bulk_main
            bulk_main()
        else:
            from server.weekly_update import main as weekly_main
            weekly_main()
    except Exception:
        logger.exception("update-all task failed")


@router.post("/update-all")
def update_all(req: UpdateAllRequest, background_tasks: BackgroundTasks):
    """Trigger full or incremental data update for all tickers (OHLC + news, alignment, layer0)."""
    background_tasks.add_task(_run_update_all, req.full)
    return {
        "status": "started",
        "mode": "full" if req.full else "incremental",
        "message": "Background update started. Check server logs for progress.",
    }


@router.post("/submit-layer1")
def submit_layer1(req: SubmitLayer1Request):
    """Submit Layer 1 (sentiment) batch to Anthropic Batch API for top N tickers. Returns batch_id for status/collect."""
    try:
        from server.batch_submit import get_top_tickers, build_batch_requests, submit_batch
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"batch_submit unavailable: {e}")

    top_n = max(1, min(200, req.top))
    tickers = get_top_tickers(top_n)
    symbols = [t["symbol"] for t in tickers]
    requests_list, mapping = build_batch_requests(symbols)
    if not requests_list:
        return {"batch_id": None, "message": "No pending articles to process."}
    batch_id = submit_batch(requests_list, mapping)
    total_articles = sum(len(v[1]) for v in mapping.values())
    return {"batch_id": batch_id, "total_articles": total_articles, "tickers": len(symbols)}


@router.post("/fetch")
def trigger_fetch(req: FetchRequest, background_tasks: BackgroundTasks):
    """Trigger Polygon data fetch for a symbol."""
    symbol = req.symbol.upper()
    today = datetime.now(timezone.utc).date()
    start = req.start or (today - timedelta(days=2 * 366)).isoformat()
    end = req.end or today.isoformat()

    background_tasks.add_task(_do_fetch, symbol, start, end)
    return {"symbol": symbol, "status": "fetch_started", "start": start, "end": end}


def _do_fetch(symbol: str, start: str, end: str):
    """Background fetch of OHLC + news data."""
    try:
        # OHLC
        ohlc_rows = fetch_ohlc(symbol, start, end)
        conn = get_conn()
        for row in ohlc_rows:
            conn.execute(
                """INSERT OR IGNORE INTO ohlc
                   (symbol, date, open, high, low, close, volume, vwap, transactions)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (symbol, row["date"], row["open"], row["high"], row["low"],
                 row["close"], row["volume"], row["vwap"], row["transactions"]),
            )
        conn.execute(
            "UPDATE tickers SET last_ohlc_fetch = ? WHERE symbol = ?",
            (end, symbol),
        )
        conn.commit()

        # News
        articles = fetch_news(symbol, start, end)
        for art in articles:
            news_id = art.get("id")
            if not news_id:
                continue
            tickers = art.get("tickers") or []
            conn.execute(
                """INSERT OR IGNORE INTO news_raw
                   (id, title, description, publisher, author,
                    published_utc, article_url, amp_url, tickers_json, insights_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (news_id, art.get("title"), art.get("description"),
                 art.get("publisher"), art.get("author"), art.get("published_utc"),
                 art.get("article_url"), art.get("amp_url"),
                 json.dumps(tickers),
                 json.dumps(art.get("insights")) if art.get("insights") else None),
            )
            for tk in tickers:
                conn.execute(
                    "INSERT OR IGNORE INTO news_ticker (news_id, symbol) VALUES (?, ?)",
                    (news_id, tk),
                )

        conn.execute(
            "UPDATE tickers SET last_news_fetch = ? WHERE symbol = ?",
            (end, symbol),
        )
        conn.commit()
        conn.close()

        # Run alignment
        align_news_for_symbol(symbol)
    except Exception:
        logger.exception("Fetch error for %s", symbol)


@router.post("/process")
def trigger_process(req: ProcessRequest):
    """Run Layer 0 filter, then submit Layer 1 batch for remaining articles."""
    symbol = req.symbol.upper()

    # Step 1: Alignment
    align_result = align_news_for_symbol(symbol)

    # Step 2: Layer 0
    l0_stats = run_layer0(symbol)

    # Step 3: Run Layer 1 (50 articles per API call)
    l1_stats = run_layer1(symbol, max_articles=req.batch_size)

    return {
        "symbol": symbol,
        "alignment": align_result,
        "layer0": l0_stats,
        "layer1": l1_stats,
    }


@router.get("/batch/{batch_id}")
def get_batch_status(batch_id: str):
    """Check status of a batch job."""
    status = check_batch_status(batch_id)

    # If ended, collect results
    if status["status"] == "ended":
        collect_stats = collect_batch_results(batch_id)
        status["collect_stats"] = collect_stats

    return status
