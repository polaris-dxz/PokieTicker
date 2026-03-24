"""Layer 2: On-demand Sonnet deep analysis.

Triggered when user clicks a news article. Cached in layer2_results.
Cost: ~$0.003/article, only on user click.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import anthropic

from server.config import settings
from server.database import get_conn
from server.anthropic_client import (
    auth_error_hint,
    format_anthropic_error,
    get_anthropic_client,
    upstream_http_status,
)

logger = logging.getLogger(__name__)

def _layer2_model() -> str:
    return (settings.anthropic_model_sonnet or "claude-sonnet-4-6").strip()


def _extract_text_from_message(message: Any) -> str:
    """Collect text from all text blocks (Anthropic may return multiple blocks)."""
    content = getattr(message, "content", None) or []
    parts: List[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def get_cached(news_id: str, symbol: str) -> Optional[Dict[str, Any]]:
    """Check if a deep analysis is already cached."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM layer2_results WHERE news_id = ? AND symbol = ?",
        (news_id, symbol),
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def analyze_article(news_id: str, symbol: str) -> Dict[str, Any]:
    """Run deep Sonnet analysis on a single article. Returns cached if available.

    On failure returns a dict with ``error`` and optional ``http_status`` (for the router).
    """
    cached = get_cached(news_id, symbol)
    if cached:
        return {
            "news_id": cached["news_id"],
            "symbol": cached["symbol"],
            "discussion": cached.get("discussion") or "",
            "growth_reasons": cached.get("growth_reasons") or "",
            "decrease_reasons": cached.get("decrease_reasons") or "",
        }

    # Fetch article data
    conn = get_conn()
    article = conn.execute(
        "SELECT title, description, article_url FROM news_raw WHERE id = ?",
        (news_id,),
    ).fetchone()
    conn.close()

    if not article:
        return {"error": "Article not found", "http_status": 404}

    api_key = (settings.anthropic_api_key or "").strip()
    if not api_key:
        return {
            "error": "Anthropic API key is not configured (set ANTHROPIC_API_KEY in .env)",
            "http_status": 503,
        }

    prompt = f"""You are a senior financial analyst. Provide a deep analysis of this news article's impact on {symbol} stock.

TITLE: {article['title']}

DESCRIPTION: {article['description'] or 'No description available'}

Provide your analysis as JSON:
{{
  "discussion": "Detailed analysis of the article's impact on {symbol} (200-300 words)",
  "growth_reasons": "Specific factors from this news that could drive {symbol} stock price up (bullet points)",
  "decrease_reasons": "Specific risk factors from this news that could drive {symbol} stock price down (bullet points)"
}}

Respond with JSON only."""

    try:
        client = get_anthropic_client()
        message = client.messages.create(
            model=_layer2_model(),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        detail = format_anthropic_error(e)
        code = upstream_http_status(e)
        hint = auth_error_hint(code)
        logger.warning("Anthropic API error in deep analysis: %s", detail)
        return {
            "error": f"Anthropic API error: {detail}{hint}",
            "http_status": code or 502,
        }
    except Exception as e:
        detail = format_anthropic_error(e)
        code = upstream_http_status(e)
        logger.exception("Unexpected error calling Anthropic for deep analysis: %s", detail)
        return {
            "error": f"Failed to call AI service: {detail}{auth_error_hint(code)}",
            "http_status": code or 502,
        }

    text = _extract_text_from_message(message)
    if not text.strip():
        return {
            "error": "AI returned an empty response. Try again or check the model name / API access.",
            "http_status": 502,
        }

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        parsed = json.loads(text[start:end]) if start >= 0 and end > start else {}
    except json.JSONDecodeError:
        parsed = {"discussion": text, "growth_reasons": "", "decrease_reasons": ""}

    # Cache result
    conn = get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO layer2_results
               (news_id, symbol, discussion, growth_reasons, decrease_reasons, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                news_id,
                symbol,
                parsed.get("discussion", ""),
                parsed.get("growth_reasons", ""),
                parsed.get("decrease_reasons", ""),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        logger.exception("Failed to cache layer2 result")
        conn.close()
        return {"error": f"Failed to save analysis: {e}", "http_status": 500}
    conn.close()

    return {
        "news_id": news_id,
        "symbol": symbol,
        "discussion": parsed.get("discussion", ""),
        "growth_reasons": parsed.get("growth_reasons", ""),
        "decrease_reasons": parsed.get("decrease_reasons", ""),
    }


def generate_story(symbol: str, csv_content: str) -> str:
    """Generate an AI story about stock price movements. Port from app.py."""
    client = get_anthropic_client()

    message = client.messages.create(
        model=_layer2_model(),
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Below is {symbol}'s OHLC data and related news. Please generate a compelling investment story based on this data.

Data:
```
{csv_content[-50000:]}
```

Story requirements:
1. Tell the complete journey of the stock price from start to end, highlighting key turning points
2. Analyze the underlying business and economic factors in conjunction with news events
3. Start the story with a brief 1-2 sentence summary of the stock's situation
4. Analyze changes in market sentiment and investment opportunities
5. Output in HTML format using <h3> headings, <p> paragraphs, <strong> emphasis tags

Write in English, approximately 500-1000 words, with vivid and narrative language. Focus on:
- Major price volatility periods with a timeline
- Impact of key news events
- Comparisons with competitors
- Regulatory environment and policy impacts""",
            }
        ],
    )

    return _extract_text_from_message(message)


def analyze_range(symbol: str, start_date: str, end_date: str, question: Optional[str] = None) -> Dict[str, Any]:
    """Analyze what drove price movement in a date range using Sonnet."""
    conn = get_conn()

    # Get OHLC data for range
    ohlc_rows = conn.execute(
        "SELECT date, open, high, low, close, volume FROM ohlc WHERE symbol = ? AND date >= ? AND date <= ? ORDER BY date ASC",
        (symbol, start_date, end_date),
    ).fetchall()

    if not ohlc_rows:
        conn.close()
        return {"error": "No OHLC data for this range"}

    open_price = ohlc_rows[0]["open"]
    close_price = ohlc_rows[-1]["close"]
    high_price = max(r["high"] for r in ohlc_rows)
    low_price = min(r["low"] for r in ohlc_rows)
    price_change_pct = round((close_price - open_price) / open_price * 100, 2)

    # Get news in range, prioritize by impact
    news_rows = conn.execute(
        """SELECT nr.title, l1.chinese_summary, l1.key_discussion,
                  l1.sentiment, l1.reason_growth, l1.reason_decrease,
                  na.trade_date, na.ret_t0
           FROM news_aligned na
           JOIN layer1_results l1 ON na.news_id = l1.news_id AND l1.symbol = na.symbol
           JOIN news_raw nr ON na.news_id = nr.id
           WHERE na.symbol = ? AND na.trade_date >= ? AND na.trade_date <= ?
             AND l1.relevance = 'relevant'
           ORDER BY ABS(COALESCE(na.ret_t0, 0)) DESC
           LIMIT 30""",
        (symbol, start_date, end_date),
    ).fetchall()
    conn.close()

    news_count = len(news_rows)

    # Build news context for prompt
    news_context = ""
    for i, row in enumerate(news_rows[:30], 1):
        ret = f"Same-day change: {row['ret_t0']*100:.2f}%" if row["ret_t0"] else ""
        news_context += f"\n{i}. [{row['trade_date']}] {row['title']}\n"
        if row["chinese_summary"]:
            news_context += f"   Summary: {row['chinese_summary']}\n"
        if ret:
            news_context += f"   {ret}\n"

    # Build OHLC summary
    ohlc_summary = f"Open: ${open_price:.2f}, Close: ${close_price:.2f}, High: ${high_price:.2f}, Low: ${low_price:.2f}, Change: {price_change_pct:+.2f}%, Trading days: {len(ohlc_rows)}"

    client = get_anthropic_client()

    question_part = f"The user's specific question is: {question}. Please focus on answering this question in your analysis.\n\n" if question else ""

    prompt = f"""You are a senior financial analyst. Please analyze {symbol}'s stock price movement from {start_date} to {end_date}.

Price data:
{ohlc_summary}

Related news during this period ({news_count} articles):
{news_context if news_context else "No related news during this period"}

{question_part}Please return the analysis in JSON format:
{{
  "summary": "A brief overview in 1-2 sentences",
  "key_events": ["Key event 1", "Key event 2", ...],
  "bullish_factors": ["Bullish factor 1", ...],
  "bearish_factors": ["Bearish factor 1", ...],
  "trend_analysis": "A detailed trend analysis in 100-150 words"
}}

Return JSON only."""

    message = client.messages.create(
        model=_layer2_model(),
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = _extract_text_from_message(message)
    try:
        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1
        analysis = json.loads(text[start_idx:end_idx]) if start_idx >= 0 and end_idx > start_idx else {}
    except json.JSONDecodeError:
        analysis = {
            "summary": text[:100],
            "key_events": [],
            "bullish_factors": [],
            "bearish_factors": [],
            "trend_analysis": text,
        }

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "price_change_pct": price_change_pct,
        "open_price": open_price,
        "close_price": close_price,
        "high_price": high_price,
        "low_price": low_price,
        "news_count": news_count,
        "trading_days": len(ohlc_rows),
        "analysis": analysis,
    }
