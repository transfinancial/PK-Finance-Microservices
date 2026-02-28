# PK Finance — Unified Dashboard & API

Single FastAPI service combining **MUFAP Mutual Funds** + **PSX Stock Exchange** data with a built-in web dashboard.

> **Cost Optimization:** Merged from 3 separate Railway services into 1, reducing hosting costs by ~60-66%.

| Data Source | API Prefix | Records |
|---|---|---|
| [MUFAP](https://www.mufap.com.pk) — Mutual Funds | `/api/mufap/...` | ~520 funds |
| [PSX](https://dps.psx.com.pk) — Stock Exchange | `/api/psx/...` | ~470 stocks |
| Frontend Dashboard | `/` | — |

Data **auto-scrapes every 30 minutes** and is served from an in-memory cache for instant responses.

---

## Quick Start

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

## API Reference

### Health

```bash
curl http://localhost:8000/api/health
```

### MUFAP Mutual Funds (`/api/mufap/...`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/mufap/` | Service info |
| GET | `/api/mufap/health` | Health check |
| GET | `/api/mufap/funds` | All funds (filter, sort, paginate) |
| GET | `/api/mufap/funds/search?q=UBL` | Search by name/category/trustee |
| GET | `/api/mufap/funds/categories` | Categories with counts |
| GET | `/api/mufap/funds/category/{name}` | Funds in a category |
| GET | `/api/mufap/funds/top-nav?limit=10` | Top N by NAV |
| GET | `/api/mufap/funds/stats` | Aggregate statistics |
| GET | `/api/mufap/export/excel` | Download Excel |
| POST | `/api/mufap/scrape/sync` | Trigger scrape (blocking) |

**Filter examples:**
```bash
curl "http://localhost:8000/api/mufap/funds?category=Equity&sort_by=nav&ascending=false&limit=20"
curl "http://localhost:8000/api/mufap/funds?min_nav=10&max_nav=100"
curl "http://localhost:8000/api/mufap/funds/search?q=HBL&field=fund_name"
```

### PSX Stock Exchange (`/api/psx/...`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/psx/` | Service info |
| GET | `/api/psx/health` | Health check |
| GET | `/api/psx/stocks` | All stocks (filter, sort, paginate) |
| GET | `/api/psx/stocks/search?symbol=HBL` | Search by symbol |
| GET | `/api/psx/stocks/{symbol}` | Single stock detail |
| GET | `/api/psx/stocks/gainers` | Top gainers |
| GET | `/api/psx/stocks/losers` | Top losers |
| GET | `/api/psx/stocks/active` | Most active by volume |
| GET | `/api/psx/stocks/summary` | Market overview |
| GET | `/api/psx/indices` | PSX indices (KSE100, etc.) |
| GET | `/api/psx/export/excel` | Download Excel |
| POST | `/api/psx/scrape/sync` | Trigger scrape (blocking) |

**Filter examples:**
```bash
curl "http://localhost:8000/api/psx/stocks?min_volume=1000000&sort_by=change_pct&ascending=false"
curl "http://localhost:8000/api/psx/stocks/gainers?limit=10"
curl "http://localhost:8000/api/psx/stocks/ENGRO"
```

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

**Tech Stack:** Python 3.12 · FastAPI · BeautifulSoup4 + lxml · Pandas · ORJSONResponse · GZip · Multi-stage Docker

---

## Project Structure

```
Microservices/
├── docker-compose.yml
├── README.md
├── unified-service/                # ← Deploy this one service
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

---

## Railway Deployment

Deploy only the `unified-service/` directory as a single Railway service. This replaces the previous 3-service setup:

| Before (3 services) | After (1 service) |
|---|---|
| Mutual Funds — $0.0030/hr | **PK Finance** — ~$0.003/hr |
| PSX — $0.0027/hr | |
| Frontend — $0.0006/hr | |
| **Total: ~$0.0063/hr** | **Total: ~$0.003/hr** |

Set **Root Directory** in Railway to `unified-service` and add env var `PORT` (Railway sets this automatically).
