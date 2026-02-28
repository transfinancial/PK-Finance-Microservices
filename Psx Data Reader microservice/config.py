"""
PSX Data Reader Microservice - Configuration
==============================================
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
EXCEL_OUTPUT_DIR = os.getenv("EXCEL_OUTPUT_DIR", "./output")
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "30"))

# PSX URLs
PSX_BASE_URL = "https://dps.psx.com.pk"
PSX_MARKET_WATCH_URL = f"{PSX_BASE_URL}/market-watch"
PSX_HOME_URL = PSX_BASE_URL
