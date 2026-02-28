# PK Finance — Unified Dashboard & API

**Live:** [https://pk.up.railway.app](https://pk.up.railway.app)

Single FastAPI service combining **MUFAP Mutual Funds** + **PSX Stock Exchange** data with a built-in PWA dashboard.

| Data Source | API Prefix | Records |
|---|---|---|
| [MUFAP](https://www.mufap.com.pk) — Mutual Funds | `/api/mufap/...` | ~520 funds |
| [PSX](https://dps.psx.com.pk) — Stock Exchange | `/api/psx/...` | ~470 stocks |
| Frontend Dashboard | `/` | [Open Dashboard](https://pk.up.railway.app) |
| Swagger UI (Auto Docs) | `/docs` | [Open Docs](https://pk.up.railway.app/docs) |

Data **auto-scrapes every 30 minutes** and is served from an in-memory cache for instant responses.

---

## Live API Base URL

```
https://pk.up.railway.app
```

All API examples below use this base URL. Replace with `http://localhost:8000` when running locally.

---

## Frontend Dashboard

**URL:** [https://pk.up.railway.app](https://pk.up.railway.app)

The dashboard is a built-in PWA (Progressive Web App) that provides:

- **Mutual Funds tab** — Browse, search, filter, and sort ~520 Pakistani mutual funds with NAV data
- **Stocks tab** — View all PSX-listed stocks with price, change, and volume data; switch between All / Gainers / Losers / Most Active / Summary views
- **Indices tab** — Live PSX indices (KSE-100, KSE-30, KMI-30, etc.)
- **Config tab** — Change API endpoints and see a full endpoint reference table
- **Mobile installable** — Add to home screen on Android/iOS for native app experience

---

## API Reference

### Health Check

```bash
curl https://pk.up.railway.app/api/health
```

Returns overall service status with cached record counts:

```json
{
  "status": "healthy",
  "mufap": { "ready": true, "cached": 519 },
  "psx": { "ready": true, "cached": 472 }
}
```

---

### MUFAP Mutual Funds (`/api/mufap/...`)

#### All Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/mufap/` | Service info (version, fund count, last scrape) |
| GET | `/api/mufap/health` | Health check with cache status |
| GET | `/api/mufap/funds` | All funds — filter, sort, paginate |
| GET | `/api/mufap/funds/search?q=` | Search by name, category, or trustee |
| GET | `/api/mufap/funds/categories` | All categories with fund counts |
| GET | `/api/mufap/funds/category/{name}` | All funds in a specific category |
| GET | `/api/mufap/funds/top-nav?limit=` | Top N funds by NAV value |
| GET | `/api/mufap/funds/stats` | Aggregate statistics (avg, min, max NAV) |
| GET | `/api/mufap/export/excel` | Download all funds as Excel (.xlsx) |
| POST | `/api/mufap/scrape` | Trigger background scrape |
| POST | `/api/mufap/scrape/sync` | Trigger scrape and wait for result |

#### Query Parameters for `/api/mufap/funds`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `category` | string | — | Filter by category (partial match) |
| `trustee` | string | — | Filter by trustee (partial match) |
| `min_nav` | float | — | Minimum NAV |
| `max_nav` | float | — | Maximum NAV |
| `sort_by` | string | `fund_name` | Column to sort by |
| `ascending` | bool | `true` | Sort direction |
| `limit` | int | `1000` | Max results (1–5000) |
| `offset` | int | `0` | Skip N results (pagination) |

#### Query Parameters for `/api/mufap/funds/search`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | string | *(required)* | Search term |
| `field` | string | `fund_name` | Column to search in |

#### Examples

```bash
# Get all funds
curl "https://pk.up.railway.app/api/mufap/funds"

# Filter by category, sorted by NAV descending, limit 20
curl "https://pk.up.railway.app/api/mufap/funds?category=Equity&sort_by=nav&ascending=false&limit=20"

# Filter by NAV range
curl "https://pk.up.railway.app/api/mufap/funds?min_nav=10&max_nav=100"

# Filter by trustee
curl "https://pk.up.railway.app/api/mufap/funds?trustee=MCB"

# Paginate — page 2 with 50 per page
curl "https://pk.up.railway.app/api/mufap/funds?limit=50&offset=50"

# Search funds by name
curl "https://pk.up.railway.app/api/mufap/funds/search?q=UBL"

# Search by category field
curl "https://pk.up.railway.app/api/mufap/funds/search?q=Equity&field=fund_category"

# Get all categories
curl "https://pk.up.railway.app/api/mufap/funds/categories"

# Get funds in a specific category
curl "https://pk.up.railway.app/api/mufap/funds/category/Equity%20Fund"

# Top 10 funds by NAV
curl "https://pk.up.railway.app/api/mufap/funds/top-nav?limit=10"

# Aggregate statistics
curl "https://pk.up.railway.app/api/mufap/funds/stats"

# Download Excel file
curl -O "https://pk.up.railway.app/api/mufap/export/excel"

# Trigger a manual scrape
curl -X POST "https://pk.up.railway.app/api/mufap/scrape/sync"
```

---

### PSX Stock Exchange (`/api/psx/...`)

#### All Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/psx/` | Service info (version, stock count, last scrape) |
| GET | `/api/psx/health` | Health check with cache status |
| GET | `/api/psx/stocks` | All stocks — filter, sort, paginate |
| GET | `/api/psx/stocks/search?symbol=` | Search stocks by symbol |
| GET | `/api/psx/stocks/{symbol}` | Single stock detail |
| GET | `/api/psx/stocks/gainers?limit=` | Top N gainers by change % |
| GET | `/api/psx/stocks/losers?limit=` | Top N losers by change % |
| GET | `/api/psx/stocks/active?limit=` | Most active by trading volume |
| GET | `/api/psx/stocks/summary` | Market overview (totals, gainers/losers count) |
| GET | `/api/psx/indices` | PSX indices (KSE-100, KSE-30, etc.) |
| GET | `/api/psx/export/excel` | Download all stocks as Excel (.xlsx) |
| POST | `/api/psx/scrape` | Trigger background scrape |
| POST | `/api/psx/scrape/sync` | Trigger scrape and wait for result |
| POST | `/api/psx/scrape/indices` | Scrape indices only |

#### Query Parameters for `/api/psx/stocks`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_price` | float | — | Minimum current price |
| `max_price` | float | — | Maximum current price |
| `min_volume` | int | — | Minimum trading volume |
| `min_change_pct` | float | — | Minimum change % |
| `max_change_pct` | float | — | Maximum change % |
| `sort_by` | string | `volume` | Column to sort by |
| `ascending` | bool | `false` | Sort direction |
| `limit` | int | `1000` | Max results (1–5000) |
| `offset` | int | `0` | Skip N results (pagination) |

#### Query Parameters for Gainers / Losers / Active

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | int | `20` | Number of results (1–100) |

#### Examples

```bash
# Get all stocks (default: sorted by volume desc)
curl "https://pk.up.railway.app/api/psx/stocks"

# Filter by minimum volume, sorted by change %
curl "https://pk.up.railway.app/api/psx/stocks?min_volume=1000000&sort_by=change_pct&ascending=false"

# Filter by price range
curl "https://pk.up.railway.app/api/psx/stocks?min_price=50&max_price=500"

# Filter by positive change only
curl "https://pk.up.railway.app/api/psx/stocks?min_change_pct=0&sort_by=change_pct&ascending=false"

# Paginate — page 3 with 100 per page
curl "https://pk.up.railway.app/api/psx/stocks?limit=100&offset=200"

# Search stocks by symbol
curl "https://pk.up.railway.app/api/psx/stocks/search?symbol=HBL"

# Get a single stock
curl "https://pk.up.railway.app/api/psx/stocks/ENGRO"

# Top 10 gainers
curl "https://pk.up.railway.app/api/psx/stocks/gainers?limit=10"

# Top 10 losers
curl "https://pk.up.railway.app/api/psx/stocks/losers?limit=10"

# Most active stocks by volume
curl "https://pk.up.railway.app/api/psx/stocks/active?limit=15"

# Market summary
curl "https://pk.up.railway.app/api/psx/stocks/summary"

# PSX indices (KSE-100, KSE-30, KMI-30, etc.)
curl "https://pk.up.railway.app/api/psx/indices"

# Download Excel file
curl -O "https://pk.up.railway.app/api/psx/export/excel"

# Trigger a manual scrape
curl -X POST "https://pk.up.railway.app/api/psx/scrape/sync"

# Scrape indices only
curl -X POST "https://pk.up.railway.app/api/psx/scrape/indices"
```

---

## Response Format

All list endpoints return a consistent JSON structure:

```json
{
  "count": 20,
  "total_filtered": 519,
  "total_available": 519,
  "offset": 0,
  "limit": 20,
  "last_scrape": "2026-02-28T14:30:00",
  "data": [
    { "fund_name": "...", "nav": 12.34, ... }
  ]
}
```

---

## Quick Start (Local Development)

### Option 1: Docker (recommended)

```bash
docker compose up -d --build
# Service available at http://localhost:8000
```

### Option 2: Run Locally

```bash
cd unified-service
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Open http://localhost:8000 for the dashboard, or http://localhost:8000/docs for Swagger UI.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `SCRAPE_INTERVAL_MINUTES` | `30` | Auto-scrape frequency |
| `EXCEL_OUTPUT_DIR` | `./output` | Excel export directory |
| `PORT` | `8000` | Server port |

---

## Architecture

```
                         ┌─────────────────────────────┐
                         │   PK Finance Unified Svc    │ :8000
   ┌─────────────┐      │                             │
   │  MUFAP Site │◄─────│  /api/mufap/*  (FastAPI)    │
   └─────────────┘      │  /api/psx/*    (FastAPI)    │      ┌──────────┐
   ┌─────────────┐      │  /            (Dashboard)   │─────►│ Browser  │
   │  PSX Site   │◄─────│                             │      └──────────┘
   └─────────────┘      │  In-memory cache + 30m loop │
                         └─────────────────────────────┘
```

**Live URL:** https://pk.up.railway.app

**Tech Stack:** Python 3.12 · FastAPI · BeautifulSoup4 + lxml · Pandas · ORJSONResponse · GZip · Multi-stage Docker

---

## Project Structure

```
Microservices/
├── docker-compose.yml
├── README.md
├── unified-service/                # ← Deployed service
│   ├── main.py                     # Combined FastAPI app
│   ├── mufap_scraper.py            # MUFAP web scraper
│   ├── psx_scraper.py              # PSX web scraper
│   ├── excel_export.py             # Excel exports (both)
│   ├── config.py                   # Unified config
│   ├── requirements.txt
│   ├── Dockerfile
│   └── static/                     # Frontend dashboard (PWA)
│       ├── index.html
│       ├── manifest.json
│       ├── sw.js
│       └── icons/
├── Mutual Funds Data Micorservice/ # Original (deprecated)
└── Psx Data Reader microservice/   # Original (deprecated)
```
