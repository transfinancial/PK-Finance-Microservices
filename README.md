# Pakistan Financial Data Microservices

Two FastAPI microservices that scrape and serve **real-time financial data** from Pakistan's markets:

| Service | Port | Data Source | Records |
|---------|------|-------------|---------|
| **MUFAP** – Mutual Funds | `8001` | [mufap.com.pk](https://www.mufap.com.pk) | ~520 funds |
| **PSX** – Stock Exchange | `8002` | [dps.psx.com.pk](https://dps.psx.com.pk) | ~470 stocks |

Both services auto-scrape every **30 minutes** and serve data from an in-memory cache for instant responses.

---

## Quick Start

### Option 1: Docker Compose (recommended)

```bash
docker compose up -d --build
```

Services will be available at:
- MUFAP: http://localhost:8001 (docs at `/docs`)
- PSX: http://localhost:8002 (docs at `/docs`)

### Option 2: Run Locally

```bash
# MUFAP service
cd "Mutual Funds Data Micorservice"
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --port 8001

# PSX service (separate terminal)
cd "Psx Data Reader microservice"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8002
```

### Configuration

Copy `.env.example` to `.env` in each service directory:

```env
EXCEL_OUTPUT_DIR=./output          # Where Excel exports are saved
SCRAPE_INTERVAL_MINUTES=30         # Auto-scrape interval
```

---

## Architecture

```
┌──────────────┐     HTTP GET      ┌────────────────┐
│  MUFAP Site  │ ◄──────────────── │  MUFAP Service │ :8001
│  (mufap.pk)  │   requests+BS4   │  (FastAPI)      │
└──────────────┘                   └───────┬────────┘
                                           │ In-memory DataFrame cache
                                           │ Auto-refresh every 30 min
┌──────────────┐     HTTP GET      ┌───────┴────────┐
│   PSX Site   │ ◄──────────────── │  PSX Service   │ :8002
│(dps.psx.pk)  │   requests+BS4   │  (FastAPI)      │
└──────────────┘                   └────────────────┘
```

**Tech Stack:**
- Python 3.12, FastAPI 3.x, Uvicorn
- BeautifulSoup4 + lxml (HTML parsing)
- Pandas (data manipulation)
- ORJSONResponse (fast JSON serialization)
- GZipMiddleware (response compression)
- Multi-stage Docker builds (~150MB images)

---

## API Reference — MUFAP Mutual Funds (port 8001)

### Service Endpoints

#### `GET /` — Service Info
```bash
curl http://localhost:8001/
```
```json
{
  "service": "MUFAP Mutual Funds Data Microservice",
  "version": "3.0.0",
  "status": "running",
  "cached_funds": 519,
  "auto_refresh_minutes": 30
}
```

#### `GET /health` — Health Check
```bash
curl http://localhost:8001/health
```
Returns `"status": "healthy"` when data is loaded, `"warming_up"` during initial scrape.

#### `POST /scrape` — Trigger Background Scrape
```bash
curl -X POST http://localhost:8001/scrape
```

#### `POST /scrape/sync` — Trigger Blocking Scrape
```bash
curl -X POST http://localhost:8001/scrape/sync
```
Returns scrape results with count immediately.

---

### Data Endpoints

#### `GET /funds` — Get All Funds (filter, sort, paginate)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | — | Filter by fund category (partial match) |
| `trustee` | string | — | Filter by trustee name (partial match) |
| `min_nav` | float | — | Minimum NAV filter |
| `max_nav` | float | — | Maximum NAV filter |
| `sort_by` | string | `fund_name` | Sort field: `fund_name`, `nav`, `fund_category`, `date_updated` |
| `ascending` | bool | `true` | Sort direction |
| `limit` | int | `1000` | Max records (1–5000) |
| `offset` | int | `0` | Pagination offset |

**Examples:**
```bash
# All funds
curl "http://localhost:8001/funds"

# Money Market funds only
curl "http://localhost:8001/funds?category=Money%20Market"

# Top 10 by NAV descending
curl "http://localhost:8001/funds?sort_by=nav&ascending=false&limit=10"

# Funds with NAV between 10 and 100
curl "http://localhost:8001/funds?min_nav=10&max_nav=100"

# Page 2 (records 50-99)
curl "http://localhost:8001/funds?limit=50&offset=50"

# Filter by trustee
curl "http://localhost:8001/funds?trustee=MCB"
```

**Response:**
```json
{
  "count": 10,
  "total_filtered": 519,
  "total_available": 519,
  "offset": 0,
  "limit": 10,
  "last_scrape": "2025-01-15T10:30:00",
  "data": [
    {
      "fund_name": "ABL Cash Fund",
      "fund_category": "Money Market",
      "inception_date": "2009-07-06",
      "offer_price": 10.85,
      "repurchase_price": 10.85,
      "nav": 10.8472,
      "date_updated": "2025-01-15",
      "trustee": "MCB Financial Services",
      "scrape_timestamp": "2025-01-15T10:30:00"
    }
  ]
}
```

#### `GET /funds/search` — Search Funds

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (partial match) |
| `field` | string | No | Field to search: `fund_name` (default), `fund_category`, `trustee` |

```bash
# Search by fund name
curl "http://localhost:8001/funds/search?q=UBL"

# Search by category
curl "http://localhost:8001/funds/search?q=Equity&field=fund_category"

# Search by trustee
curl "http://localhost:8001/funds/search?q=MCB&field=trustee"
```

#### `GET /funds/categories` — List All Categories with Counts
```bash
curl http://localhost:8001/funds/categories
```
```json
{
  "total_categories": 15,
  "categories": [
    {"category": "Aggressive Fixed Income", "count": 12},
    {"category": "Equity", "count": 85},
    {"category": "Money Market", "count": 42}
  ]
}
```

#### `GET /funds/category/{category}` — Funds by Category
```bash
curl "http://localhost:8001/funds/category/Equity"
```

#### `GET /funds/top-nav` — Top Funds by NAV

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | `20` | Number of top funds (1–100) |
| `category` | string | — | Optional category filter |

```bash
curl "http://localhost:8001/funds/top-nav?limit=5"
curl "http://localhost:8001/funds/top-nav?limit=10&category=Equity"
```

#### `GET /funds/stats` — Aggregate Statistics

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | — | Optional category filter |

```bash
curl http://localhost:8001/funds/stats
curl "http://localhost:8001/funds/stats?category=Money%20Market"
```
```json
{
  "total_funds": 519,
  "total_categories": 15,
  "nav": {
    "mean": 32.4521,
    "median": 13.8234,
    "min": 0.0102,
    "max": 3256.78,
    "std": 125.45
  },
  "offer_price": {"mean": 32.51, "min": 0.01, "max": 3260.0},
  "data_date": "2025-01-15",
  "trustees": ["CDC", "MCB Financial Services", ...]
}
```

#### `GET /export/excel` — Download Excel File
```bash
curl -O http://localhost:8001/export/excel
```

---

## API Reference — PSX Stock Exchange (port 8002)

### Service Endpoints

#### `GET /` — Service Info
```bash
curl http://localhost:8002/
```

#### `GET /health` — Health Check
```bash
curl http://localhost:8002/health
```

#### `POST /scrape` — Background Scrape
```bash
curl -X POST http://localhost:8002/scrape
```

#### `POST /scrape/sync` — Blocking Scrape
```bash
curl -X POST http://localhost:8002/scrape/sync
```

#### `POST /scrape/indices` — Scrape Index Data
```bash
curl -X POST http://localhost:8002/scrape/indices
```

---

### Data Endpoints

#### `GET /stocks` — Get All Stocks (filter, sort, paginate)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_price` | float | — | Minimum current price |
| `max_price` | float | — | Maximum current price |
| `min_volume` | int | — | Minimum volume |
| `min_change_pct` | float | — | Minimum change % |
| `max_change_pct` | float | — | Maximum change % |
| `sort_by` | string | `volume` | Sort field: `symbol`, `current`, `change`, `change_pct`, `volume` |
| `ascending` | bool | `false` | Sort direction |
| `limit` | int | `1000` | Max records (1–5000) |
| `offset` | int | `0` | Pagination offset |

**Examples:**
```bash
# All stocks sorted by volume
curl "http://localhost:8002/stocks"

# Stocks priced under 50 PKR
curl "http://localhost:8002/stocks?max_price=50"

# High-volume stocks (> 1M shares)
curl "http://localhost:8002/stocks?min_volume=1000000"

# Stocks with > 2% gain
curl "http://localhost:8002/stocks?min_change_pct=2"

# Sort by price descending
curl "http://localhost:8002/stocks?sort_by=current&ascending=false&limit=20"

# Page 3 (records 100-149)
curl "http://localhost:8002/stocks?limit=50&offset=100"
```

**Response:**
```json
{
  "count": 20,
  "total_filtered": 472,
  "total": 472,
  "offset": 0,
  "limit": 20,
  "last_scrape": "2025-01-15T10:30:00",
  "data": [
    {
      "symbol": "HBL",
      "ldcp": 245.50,
      "open": 246.00,
      "high": 248.75,
      "low": 244.10,
      "current": 247.80,
      "change": 2.30,
      "change_pct": 0.94,
      "volume": 1250000,
      "date": "2025-01-15",
      "scrape_timestamp": "2025-01-15T10:30:00"
    }
  ]
}
```

#### `GET /stocks/search` — Search by Symbol
```bash
curl "http://localhost:8002/stocks/search?symbol=HBL"
curl "http://localhost:8002/stocks/search?symbol=OGD"
```

#### `GET /stocks/{symbol}` — Single Stock Detail
```bash
curl http://localhost:8002/stocks/HBL
curl http://localhost:8002/stocks/OGDC
```
```json
{
  "symbol": "HBL",
  "data": {
    "symbol": "HBL",
    "ldcp": 245.50,
    "open": 246.00,
    "high": 248.75,
    "low": 244.10,
    "current": 247.80,
    "change": 2.30,
    "change_pct": 0.94,
    "volume": 1250000
  }
}
```

#### `GET /stocks/gainers` — Top Gainers
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | `20` | Number of results (1–100) |

```bash
curl "http://localhost:8002/stocks/gainers?limit=10"
```

#### `GET /stocks/losers` — Top Losers
```bash
curl "http://localhost:8002/stocks/losers?limit=10"
```

#### `GET /stocks/active` — Most Active by Volume
```bash
curl "http://localhost:8002/stocks/active?limit=10"
```

#### `GET /stocks/summary` — Market Overview
```bash
curl http://localhost:8002/stocks/summary
```
```json
{
  "total_stocks": 472,
  "gainers": 185,
  "losers": 142,
  "unchanged": 145,
  "total_volume": 285000000,
  "avg_change_pct": 0.32,
  "market_date": "2025-01-15",
  "last_scrape": "2025-01-15T10:30:00"
}
```

#### `GET /indices` — PSX Index Data
```bash
curl http://localhost:8002/indices
```
Returns KSE100, KSE30, KMI30, etc. with current values and changes.

#### `GET /export/excel` — Download Excel Report
```bash
curl -O http://localhost:8002/export/excel
```

---

## Using These APIs From Other Projects

### Python (requests)

```python
import requests

# Get all mutual funds
resp = requests.get("http://localhost:8001/funds?limit=5000")
funds = resp.json()["data"]

# Get stocks with filters
resp = requests.get("http://localhost:8002/stocks", params={
    "min_volume": 500000,
    "sort_by": "change_pct",
    "ascending": False,
    "limit": 20,
})
top_movers = resp.json()["data"]

# Search for a specific fund
resp = requests.get("http://localhost:8001/funds/search", params={"q": "HBL"})
hbl_funds = resp.json()["data"]
```

### JavaScript / Node.js (fetch)

```javascript
// Get market summary
const res = await fetch("http://localhost:8002/stocks/summary");
const summary = await res.json();
console.log(`Gainers: ${summary.gainers}, Losers: ${summary.losers}`);

// Get top 10 gainers
const gainers = await fetch("http://localhost:8002/stocks/gainers?limit=10");
const data = await gainers.json();
data.data.forEach(s => console.log(`${s.symbol}: +${s.change_pct}%`));

// Search mutual funds
const funds = await fetch("http://localhost:8001/funds/search?q=Equity&field=fund_category");
const result = await funds.json();
```

### C# / .NET (HttpClient)

```csharp
using var client = new HttpClient();

// Get all stocks
var response = await client.GetAsync("http://localhost:8002/stocks?limit=100");
var json = await response.Content.ReadAsStringAsync();
var result = JsonSerializer.Deserialize<StockResponse>(json);
```

### cURL Examples

```bash
# Trigger a fresh scrape and wait for result
curl -X POST http://localhost:8001/scrape/sync

# Get funds filtered by category, sorted by NAV
curl "http://localhost:8001/funds?category=Equity&sort_by=nav&ascending=false&limit=20"

# Get stock detail
curl http://localhost:8002/stocks/ENGRO

# Download Excel report
curl -O -J http://localhost:8002/export/excel
```

---

## Interactive Dashboards

Both services include built-in HTML dashboards:

- **MUFAP Dashboard**: Open `Mutual Funds Data Micorservice/frontend.html` in a browser
- **PSX Dashboard**: Open `Psx Data Reader microservice/frontend.html` in a browser

Set the API URL in the top-right corner to match your running service address.

---

## Docker

### Build & Run

```bash
# Build and start both services
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Resource Limits (configured in docker-compose.yml)

Each service is limited to 256MB RAM and 0.5 CPU cores.

### Health Checks

Both containers have built-in health checks that ping `/health` every 60 seconds.

---

## Project Structure

```
Microservices/
├── docker-compose.yml              # Orchestrates both services
├── README.md                       # This file
│
├── Mutual Funds Data Micorservice/
│   ├── main.py                     # FastAPI app (port 8001)
│   ├── scraper.py                  # MUFAP web scraper
│   ├── config.py                   # Configuration
│   ├── excel_export.py             # Excel export with formatting
│   ├── frontend.html               # Interactive dashboard
│   ├── Dockerfile                  # Multi-stage Docker build
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment template
│   └── .dockerignore
│
└── Psx Data Reader microservice/
    ├── main.py                     # FastAPI app (port 8002)
    ├── scraper.py                  # PSX web scraper
    ├── config.py                   # Configuration
    ├── excel_export.py             # Excel export with charts
    ├── frontend.html               # Interactive dashboard
    ├── Dockerfile                  # Multi-stage Docker build
    ├── requirements.txt            # Python dependencies
    ├── .env.example                # Environment template
    └── .dockerignore
```

---

## Data Refresh

- Both services scrape their respective data sources **on startup**
- Auto-refresh runs every **30 minutes** (configurable via `SCRAPE_INTERVAL_MINUTES`)
- Manual scrape available via `POST /scrape` (background) or `POST /scrape/sync` (blocking)
- All data is served from an in-memory cache — responses are instant

## OpenAPI / Swagger Docs

Both services have auto-generated interactive API documentation:

- MUFAP: http://localhost:8001/docs
- PSX: http://localhost:8002/docs
