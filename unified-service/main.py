"""
PK Finance Unified Service
============================
Single FastAPI application combining:
  - MUFAP Mutual Funds API  → /api/mufap/...
  - PSX Stock Exchange API   → /api/psx/...
  - Static frontend dashboard → /

Merging 3 Railway services into 1 reduces hosting cost by ~60-66%.
"""

import os
import asyncio
import logging
from datetime import timedelta
from contextlib import asynccontextmanager
from typing import Optional
from threading import Lock
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, APIRouter
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd

from config import EXCEL_OUTPUT_DIR, SCRAPE_INTERVAL_MINUTES, now_utc5
from mufap_scraper import scrape_mufap_nav_data
from psx_scraper import scrape_psx_market_watch, scrape_psx_indices

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  In-memory caches
# ══════════════════════════════════════════════════════════════════

# MUFAP
_mufap_data: Optional[pd.DataFrame] = None
_mufap_last_scrape: Optional[str] = None
_mufap_scrape_count: int = 0
_mufap_lock = Lock()
_mufap_category_cache: list[dict] = []
_mufap_stats_cache: dict = {}

# PSX
_psx_stock_data: Optional[pd.DataFrame] = None
_psx_index_data: Optional[pd.DataFrame] = None
_psx_last_scrape: Optional[str] = None
_psx_scrape_count: int = 0
_psx_lock = Lock()
_psx_summary_cache: dict = {}

_next_scrape_time: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  MUFAP helpers
# ══════════════════════════════════════════════════════════════════

def _mufap_rebuild_caches(df: pd.DataFrame):
    global _mufap_category_cache, _mufap_stats_cache
    cat_counts = df["fund_category"].value_counts()
    _mufap_category_cache = [
        {"category": k, "count": int(v)} for k, v in sorted(cat_counts.items())
    ]
    nav = df["nav"]
    _mufap_stats_cache = {
        "total_funds": len(df),
        "total_categories": int(df["fund_category"].nunique()),
        "nav": {
            "mean": round(float(nav.mean()), 4),
            "median": round(float(nav.median()), 4),
            "min": round(float(nav.min()), 4),
            "max": round(float(nav.max()), 4),
            "std": round(float(nav.std()), 4),
        },
        "offer_price": {
            "mean": round(float(df["offer_price"].mean()), 4) if "offer_price" in df.columns else None,
            "min": round(float(df["offer_price"].min()), 4) if "offer_price" in df.columns else None,
            "max": round(float(df["offer_price"].max()), 4) if "offer_price" in df.columns else None,
        },
        "data_date": df["date_updated"].mode().iloc[0] if not df["date_updated"].mode().empty else None,
        "trustees": sorted(df["trustee"].dropna().unique().tolist()) if "trustee" in df.columns else [],
    }


def _mufap_scrape():
    global _mufap_data, _mufap_last_scrape, _mufap_scrape_count
    if not _mufap_lock.acquire(blocking=False):
        logger.info("MUFAP scrape already running – skipping")
        return {"status": "skipped", "reason": "already_running"}
    try:
        logger.info("Starting MUFAP scrape...")
        df = scrape_mufap_nav_data()
        if df.empty:
            logger.warning("MUFAP scrape returned no data")
            return {"status": "no_data", "count": 0}
        _mufap_data = df
        _mufap_last_scrape = now_utc5().isoformat()
        _mufap_scrape_count += 1
        _mufap_rebuild_caches(df)
        from excel_export import save_to_excel
        excel_path = save_to_excel(df)
        logger.info(f"MUFAP data saved: {excel_path}")
        return {"status": "success", "count": len(df), "scraped_at": _mufap_last_scrape}
    except Exception as e:
        logger.error(f"MUFAP scrape failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        _mufap_lock.release()


def _get_mufap_data() -> pd.DataFrame:
    if _mufap_data is not None and not _mufap_data.empty:
        return _mufap_data
    raise HTTPException(404, "No MUFAP data yet. Service is still loading.")


# ══════════════════════════════════════════════════════════════════
#  PSX helpers
# ══════════════════════════════════════════════════════════════════

def _psx_rebuild_caches(df: pd.DataFrame):
    global _psx_summary_cache
    total = len(df)
    gainers = int((df["change"] > 0).sum()) if "change" in df.columns else 0
    losers = int((df["change"] < 0).sum()) if "change" in df.columns else 0
    unchanged = total - gainers - losers
    total_volume = int(df["volume"].sum()) if "volume" in df.columns else 0
    _psx_summary_cache = {
        "total_stocks": total,
        "gainers": gainers,
        "losers": losers,
        "unchanged": unchanged,
        "total_volume": total_volume,
        "avg_change_pct": round(float(df["change_pct"].mean()), 2) if "change_pct" in df.columns else None,
        "total_traded_value": round(float((df["current"] * df["volume"]).sum()), 0) if {"current", "volume"} <= set(df.columns) else None,
        "market_date": df["date"].iloc[0] if "date" in df.columns and not df.empty else None,
    }


def _psx_scrape():
    global _psx_stock_data, _psx_index_data, _psx_last_scrape, _psx_scrape_count
    if not _psx_lock.acquire(blocking=False):
        logger.info("PSX scrape already running – skipping")
        return {"status": "skipped", "reason": "already_running"}
    try:
        logger.info("Starting PSX scrape...")
        df_stocks = scrape_psx_market_watch()
        if df_stocks.empty:
            logger.warning("PSX scrape returned no data")
            return {"status": "no_data", "stocks": 0, "indices": 0}
        _psx_stock_data = df_stocks
        _psx_last_scrape = now_utc5().isoformat()
        _psx_scrape_count += 1
        _psx_rebuild_caches(df_stocks)
        from excel_export import save_stocks_to_excel
        excel_path = save_stocks_to_excel(df_stocks)
        df_indices = scrape_psx_indices()
        _psx_index_data = df_indices
        return {"status": "success", "stocks": len(df_stocks), "indices": len(df_indices), "scraped_at": _psx_last_scrape}
    except Exception as e:
        logger.error(f"PSX scrape failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        _psx_lock.release()


def _get_psx_data() -> pd.DataFrame:
    if _psx_stock_data is not None and not _psx_stock_data.empty:
        return _psx_stock_data
    raise HTTPException(404, "No PSX data yet. Service is still loading.")


# ══════════════════════════════════════════════════════════════════
#  Background scrape loop (single loop for both sources)
# ══════════════════════════════════════════════════════════════════

async def _scrape_loop():
    while True:
        global _next_scrape_time
        _next_scrape_time = (now_utc5() + timedelta(minutes=SCRAPE_INTERVAL_MINUTES)).isoformat()
        await asyncio.sleep(SCRAPE_INTERVAL_MINUTES * 60)
        await asyncio.to_thread(_mufap_scrape)
        await asyncio.to_thread(_psx_scrape)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  PK Finance Unified Service Starting...")
    logger.info(f"  Scrape interval: every {SCRAPE_INTERVAL_MINUTES} min")
    logger.info("=" * 60)
    os.makedirs(EXCEL_OUTPUT_DIR, exist_ok=True)

    # Initial scrape (both sources, in threads)
    await asyncio.to_thread(_mufap_scrape)
    await asyncio.to_thread(_psx_scrape)

    # Start repeating loop
    task = asyncio.create_task(_scrape_loop())
    logger.info(f"Background scrape loop started – {SCRAPE_INTERVAL_MINUTES} min interval")
    yield
    task.cancel()
    logger.info("PK Finance Unified Service shutting down")


# ══════════════════════════════════════════════════════════════════
#  App + Routers
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="PK Finance Unified Service",
    description=(
        "Combined API for Pakistan financial data.\n\n"
        "- **MUFAP Mutual Funds** → `/api/mufap/...`\n"
        "- **PSX Stock Exchange** → `/api/psx/...`\n"
        "- **Dashboard** → `/`"
    ),
    version="4.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Root health ──────────────────────────────────────────────────

@app.get("/api/health")
async def unified_health():
    mufap_ok = _mufap_data is not None and not _mufap_data.empty
    psx_ok = _psx_stock_data is not None and not _psx_stock_data.empty
    return {
        "status": "healthy" if (mufap_ok and psx_ok) else "warming_up",
        "mufap": {"ready": mufap_ok, "cached": len(_mufap_data) if mufap_ok else 0, "last_scrape": _mufap_last_scrape},
        "psx": {"ready": psx_ok, "cached": len(_psx_stock_data) if psx_ok else 0, "last_scrape": _psx_last_scrape},
        "next_scrape": _next_scrape_time,
    }


# ══════════════════════════════════════════════════════════════════
#  MUFAP Router  →  /api/mufap/...
# ══════════════════════════════════════════════════════════════════

mufap = APIRouter(prefix="/api/mufap", tags=["MUFAP Mutual Funds"])


@mufap.get("/")
async def mufap_root():
    return {
        "service": "MUFAP Mutual Funds",
        "status": "running",
        "last_scrape": _mufap_last_scrape,
        "scrape_count": _mufap_scrape_count,
        "cached_funds": len(_mufap_data) if _mufap_data is not None else 0,
        "auto_refresh_minutes": SCRAPE_INTERVAL_MINUTES,
    }


@mufap.get("/health")
async def mufap_health():
    has_data = _mufap_data is not None and not _mufap_data.empty
    return {
        "status": "healthy" if has_data else "warming_up",
        "ready": has_data,
        "last_scrape": _mufap_last_scrape,
        "scrape_count": _mufap_scrape_count,
        "cached_records": len(_mufap_data) if has_data else 0,
        "next_scrape": _next_scrape_time,
    }


@mufap.post("/scrape")
async def mufap_trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(_mufap_scrape)
    return {"status": "scrape_started", "message": "Scraping MUFAP in background."}


@mufap.post("/scrape/sync")
async def mufap_scrape_sync():
    return _mufap_scrape()


@mufap.get("/funds")
async def get_funds(
    category: Optional[str] = Query(None),
    trustee: Optional[str] = Query(None),
    min_nav: Optional[float] = Query(None, ge=0),
    max_nav: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("fund_name"),
    ascending: bool = Query(True),
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    df = _get_mufap_data()
    if category:
        df = df[df["fund_category"].str.contains(category, case=False, na=False)]
    if trustee:
        df = df[df["trustee"].str.contains(trustee, case=False, na=False)]
    if min_nav is not None:
        df = df[df["nav"] >= min_nav]
    if max_nav is not None:
        df = df[df["nav"] <= max_nav]
    total_filtered = len(df)
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending, na_position="last")
    df = df.iloc[offset: offset + limit]
    return {
        "count": len(df), "total_filtered": total_filtered,
        "total_available": len(_mufap_data), "offset": offset, "limit": limit,
        "last_scrape": _mufap_last_scrape, "data": df.to_dict(orient="records"),
    }


@mufap.get("/funds/search")
async def search_funds(
    q: str = Query(..., min_length=1),
    field: str = Query("fund_name"),
):
    df = _get_mufap_data()
    if field not in df.columns:
        raise HTTPException(400, f"Invalid field '{field}'")
    df = df[df[field].str.contains(q, case=False, na=False)]
    return {"query": q, "field": field, "count": len(df), "data": df.to_dict(orient="records")}


@mufap.get("/funds/categories")
async def list_categories():
    _get_mufap_data()
    return {"total_categories": len(_mufap_category_cache), "categories": _mufap_category_cache}


@mufap.get("/funds/category/{category}")
async def get_funds_by_category(category: str):
    df = _get_mufap_data()
    df = df[df["fund_category"].str.contains(category, case=False, na=False)]
    if df.empty:
        raise HTTPException(404, f"No funds for category '{category}'")
    return {"category": category, "count": len(df), "data": df.to_dict(orient="records")}


@mufap.get("/funds/top-nav")
async def top_nav_funds(limit: int = Query(20, ge=1, le=100), category: Optional[str] = Query(None)):
    df = _get_mufap_data()
    if category:
        df = df[df["fund_category"].str.contains(category, case=False, na=False)]
    df = df.nlargest(limit, "nav")
    return {"count": len(df), "data": df.to_dict(orient="records")}


@mufap.get("/funds/stats")
async def fund_stats(category: Optional[str] = Query(None)):
    if category is None:
        _get_mufap_data()
        return {**_mufap_stats_cache, "last_scrape": _mufap_last_scrape, "category_filter": None}
    df = _get_mufap_data()
    df = df[df["fund_category"].str.contains(category, case=False, na=False)]
    if df.empty:
        raise HTTPException(404, "No data matches the filter")
    nav = df["nav"]
    return {
        "total_funds": len(df), "total_categories": int(df["fund_category"].nunique()),
        "nav": {"mean": round(float(nav.mean()), 4), "median": round(float(nav.median()), 4),
                "min": round(float(nav.min()), 4), "max": round(float(nav.max()), 4),
                "std": round(float(nav.std()), 4)},
        "last_scrape": _mufap_last_scrape, "category_filter": category,
    }


@mufap.get("/export/excel")
async def mufap_export_excel():
    if not os.path.exists(EXCEL_OUTPUT_DIR):
        raise HTTPException(404, "No Excel files available")
    files = sorted([f for f in os.listdir(EXCEL_OUTPUT_DIR) if f.startswith("mutual_funds") and f.endswith(".xlsx")], reverse=True)
    if not files:
        if _mufap_data is not None and not _mufap_data.empty:
            from excel_export import save_to_excel
            filepath = save_to_excel(_mufap_data)
            return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=os.path.basename(filepath))
        raise HTTPException(404, "No Excel files available.")
    filepath = os.path.join(EXCEL_OUTPUT_DIR, files[0])
    return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=files[0])


app.include_router(mufap)


# ══════════════════════════════════════════════════════════════════
#  PSX Router  →  /api/psx/...
# ══════════════════════════════════════════════════════════════════

psx = APIRouter(prefix="/api/psx", tags=["PSX Stock Exchange"])


@psx.get("/")
async def psx_root():
    return {
        "service": "PSX Stock Exchange",
        "status": "running",
        "last_scrape": _psx_last_scrape,
        "scrape_count": _psx_scrape_count,
        "cached_stocks": len(_psx_stock_data) if _psx_stock_data is not None else 0,
        "auto_refresh_minutes": SCRAPE_INTERVAL_MINUTES,
    }


@psx.get("/health")
async def psx_health():
    has_data = _psx_stock_data is not None and not _psx_stock_data.empty
    return {
        "status": "healthy" if has_data else "warming_up",
        "ready": has_data,
        "last_scrape": _psx_last_scrape,
        "scrape_count": _psx_scrape_count,
        "cached_stocks": len(_psx_stock_data) if has_data else 0,
        "cached_indices": len(_psx_index_data) if _psx_index_data is not None else 0,
        "next_scrape": _next_scrape_time,
    }


@psx.post("/scrape")
async def psx_trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(_psx_scrape)
    return {"status": "scrape_started", "message": "Scraping PSX in background."}


@psx.post("/scrape/sync")
async def psx_scrape_sync():
    return _psx_scrape()


@psx.post("/scrape/indices")
async def psx_scrape_indices():
    global _psx_index_data
    df = scrape_psx_indices()
    _psx_index_data = df
    records = df.to_dict(orient="records") if not df.empty else []
    return {"count": len(records), "data": records}


@psx.get("/stocks")
async def get_all_stocks(
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("volume"),
    ascending: bool = Query(False),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_volume: Optional[int] = Query(None, ge=0),
    min_change_pct: Optional[float] = Query(None),
    max_change_pct: Optional[float] = Query(None),
):
    df = _get_psx_data()
    if min_price is not None and "current" in df.columns:
        df = df[df["current"] >= min_price]
    if max_price is not None and "current" in df.columns:
        df = df[df["current"] <= max_price]
    if min_volume is not None and "volume" in df.columns:
        df = df[df["volume"] >= min_volume]
    if min_change_pct is not None and "change_pct" in df.columns:
        df = df[df["change_pct"] >= min_change_pct]
    if max_change_pct is not None and "change_pct" in df.columns:
        df = df[df["change_pct"] <= max_change_pct]
    total_filtered = len(df)
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending, na_position="last")
    df = df.iloc[offset: offset + limit]
    return {
        "count": len(df), "total_filtered": total_filtered,
        "total": len(_psx_stock_data), "offset": offset, "limit": limit,
        "last_scrape": _psx_last_scrape, "data": df.to_dict(orient="records"),
    }


@psx.get("/stocks/search")
async def search_stocks(symbol: str = Query(..., min_length=1)):
    df = _get_psx_data()
    df = df[df["symbol"].str.contains(symbol.upper(), case=False, na=False)]
    return {"count": len(df), "data": df.to_dict(orient="records")}


@psx.get("/stocks/gainers")
async def top_gainers(limit: int = Query(20, ge=1, le=100)):
    df = _get_psx_data()
    df = df[df["change"] > 0].nlargest(limit, "change_pct")
    return {"count": len(df), "data": df.to_dict(orient="records")}


@psx.get("/stocks/losers")
async def top_losers(limit: int = Query(20, ge=1, le=100)):
    df = _get_psx_data()
    df = df[df["change"] < 0].nsmallest(limit, "change_pct")
    return {"count": len(df), "data": df.to_dict(orient="records")}


@psx.get("/stocks/active")
async def most_active(limit: int = Query(20, ge=1, le=100)):
    df = _get_psx_data()
    df = df.nlargest(limit, "volume")
    return {"count": len(df), "data": df.to_dict(orient="records")}


@psx.get("/stocks/summary")
async def market_summary():
    _get_psx_data()
    return {
        **_psx_summary_cache,
        "last_scrape": _psx_last_scrape,
        "scrape_count": _psx_scrape_count,
        "auto_refresh_minutes": SCRAPE_INTERVAL_MINUTES,
    }


@psx.get("/stocks/{symbol}")
async def stock_detail(symbol: str):
    df = _get_psx_data()
    match = df[df["symbol"].str.upper() == symbol.upper()]
    if match.empty:
        raise HTTPException(404, f"Stock '{symbol}' not found")
    return {"symbol": symbol.upper(), "data": match.iloc[0].to_dict()}


@psx.get("/indices")
async def get_all_indices():
    if _psx_index_data is not None and not _psx_index_data.empty:
        return {"count": len(_psx_index_data), "data": _psx_index_data.to_dict(orient="records")}
    raise HTTPException(404, "No index data. Scrape will run automatically.")


@psx.get("/export/excel")
async def psx_export_excel():
    if not os.path.exists(EXCEL_OUTPUT_DIR):
        raise HTTPException(404, "No Excel files available")
    files = sorted([f for f in os.listdir(EXCEL_OUTPUT_DIR) if f.startswith("psx_") and f.endswith(".xlsx")], reverse=True)
    if not files:
        if _psx_stock_data is not None and not _psx_stock_data.empty:
            from excel_export import save_stocks_to_excel
            filepath = save_stocks_to_excel(_psx_stock_data)
            return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=os.path.basename(filepath))
        raise HTTPException(404, "No Excel files. Scrape will run automatically.")
    filepath = os.path.join(EXCEL_OUTPUT_DIR, files[0])
    return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=files[0])


app.include_router(psx)


# ══════════════════════════════════════════════════════════════════
#  Static files (frontend) — must be LAST
# ══════════════════════════════════════════════════════════════════

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
