/**
 * OpenClaw Skill: PokieTicker
 * Proxies requests to PokieTicker FastAPI backend based on action.
 */

const DEFAULT_BASE = "http://localhost:8000";

/**
 * @param {{ action: string, symbol?: string, q?: string, date?: string, start?: string, end?: string, window?: number, horizon?: string, top_k?: number, start_date?: string, end_date?: string }} params
 * @param {{ secrets?: { POKIETICKER_BASE_URL?: string } }} ctx
 */
export async function run(params, ctx = {}) {
  const base = (ctx.secrets && ctx.secrets.POKIETICKER_BASE_URL) || DEFAULT_BASE;
  const baseUrl = base.replace(/\/$/, "") + "/api";
  const action = params && params.action;

  if (!action) {
    return { ok: false, error: "Missing required parameter: action" };
  }

  const symbol = params.symbol ? String(params.symbol).toUpperCase() : null;

  try {
    switch (action) {
      case "list_tickers": {
        const res = await fetch(`${baseUrl}/stocks`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "search_tickers": {
        const q = params.q;
        if (!q) return { ok: false, error: "search_tickers requires 'q'" };
        const res = await fetch(`${baseUrl}/stocks/search?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "ohlc": {
        if (!symbol) return { ok: false, error: "ohlc requires 'symbol'" };
        const search = new URLSearchParams();
        if (params.start) search.set("start", params.start);
        if (params.end) search.set("end", params.end);
        const qs = search.toString();
        const res = await fetch(`${baseUrl}/stocks/${symbol}/ohlc${qs ? "?" + qs : ""}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "news": {
        if (!symbol) return { ok: false, error: "news requires 'symbol'" };
        const search = new URLSearchParams();
        if (params.date) search.set("date", params.date);
        const qs = search.toString();
        const res = await fetch(`${baseUrl}/news/${symbol}${qs ? "?" + qs : ""}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "news_range": {
        if (!symbol) return { ok: false, error: "news_range requires 'symbol'" };
        const start = params.start || params.start_date;
        const end = params.end || params.end_date;
        if (!start || !end) return { ok: false, error: "news_range requires 'start' and 'end' (or start_date/end_date)" };
        const res = await fetch(`${baseUrl}/news/${symbol}/range?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "news_categories": {
        if (!symbol) return { ok: false, error: "news_categories requires 'symbol'" };
        const res = await fetch(`${baseUrl}/news/${symbol}/categories`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "forecast": {
        if (!symbol) return { ok: false, error: "forecast requires 'symbol'" };
        const window = params.window != null ? Math.min(60, Math.max(3, Number(params.window))) : 7;
        const res = await fetch(`${baseUrl}/predict/${symbol}/forecast?window=${window}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "prediction": {
        if (!symbol) return { ok: false, error: "prediction requires 'symbol'" };
        const horizon = params.horizon === "t5" ? "t5" : "t1";
        const res = await fetch(`${baseUrl}/predict/${symbol}?horizon=${horizon}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "backtest": {
        if (!symbol) return { ok: false, error: "backtest requires 'symbol'" };
        const horizon = params.horizon === "t5" ? "t5" : "t1";
        const res = await fetch(`${baseUrl}/predict/${symbol}/backtest?horizon=${horizon}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "similar_days": {
        if (!symbol) return { ok: false, error: "similar_days requires 'symbol'" };
        const date = params.date;
        if (!date) return { ok: false, error: "similar_days requires 'date'" };
        const topK = params.top_k != null ? Math.min(30, Math.max(1, Number(params.top_k))) : 10;
        const res = await fetch(`${baseUrl}/predict/${symbol}/similar-days?date=${encodeURIComponent(date)}&top_k=${topK}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "story": {
        if (!symbol) return { ok: false, error: "story requires 'symbol'" };
        const res = await fetch(`${baseUrl}/analysis/story`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol }),
        });
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "range_local": {
        if (!symbol) return { ok: false, error: "range_local requires 'symbol'" };
        const start_date = params.start_date || params.start;
        const end_date = params.end_date || params.end;
        if (!start_date || !end_date) return { ok: false, error: "range_local requires start_date and end_date (or start/end)" };
        const res = await fetch(`${baseUrl}/analysis/range-local`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol, start_date, end_date, question: params.question || null }),
        });
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "update_data": {
        const full = Boolean(params.full);
        const res = await fetch(`${baseUrl}/pipeline/update-all`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ full }),
        });
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "fetch_data": {
        if (!symbol) return { ok: false, error: "fetch_data requires 'symbol'" };
        const res = await fetch(`${baseUrl}/pipeline/fetch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol,
            start: params.start || undefined,
            end: params.end || undefined,
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "process_data": {
        if (!symbol) return { ok: false, error: "process_data requires 'symbol'" };
        const batch_size = params.batch_size != null ? Math.max(1, Number(params.batch_size)) : 1000;
        const res = await fetch(`${baseUrl}/pipeline/process`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol, batch_size }),
        });
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "submit_layer1": {
        const top = params.top != null ? Math.min(200, Math.max(1, Number(params.top))) : 50;
        const res = await fetch(`${baseUrl}/pipeline/submit-layer1`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ top }),
        });
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      case "batch_status": {
        const batch_id = params.batch_id;
        if (!batch_id) return { ok: false, error: "batch_status requires 'batch_id'" };
        const res = await fetch(`${baseUrl}/pipeline/batch/${encodeURIComponent(batch_id)}`);
        if (!res.ok) throw new Error(await res.text());
        return { ok: true, data: await res.json() };
      }

      default:
        return { ok: false, error: `Unknown action: ${action}` };
    }
  } catch (err) {
    const message = err && (err.message || String(err));
    return { ok: false, error: message };
  }
}
