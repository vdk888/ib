#!/usr/bin/env python3
"""
Configuration file for Uncle Stock Portfolio system
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Portfolio Targeting Configuration
MAX_RANKED_STOCKS = 30  # Only top N ranked stocks get allocation, others get 0%

# Allocation Configuration
MAX_ALLOCATION = 0.10  # 10% - allocation for rank 1 stock
MIN_ALLOCATION = 0.01  # 1% - allocation for worst ranked stock (rank MAX_RANKED_STOCKS)

# Uncle Stock API Configuration for dynamic stock selection
UNCLE_STOCK_USER_ID = os.getenv("UNCLE_STOCK_USER_ID", "id missing")

# Screen names to use - these are the actual query names in Uncle Stock
UNCLE_STOCK_SCREENS = {
    "quality_bloom": "quality bloom",
    "TOR_Surplus": "TOR Surplus",
    "Moat_Companies": "Moat Companies"
}
MONTHLY_REFRESH_DAY = 1  # First day of month for stock list updates

# Additional fields configuration for universe.json
# Format: List of tuples (header_name, subtitle_pattern, field_alias, description)
# field_alias will be the key name in the JSON output
ADDITIONAL_FIELDS = [
    # Price-related fields
    ('Price', '180d change', 'price_180d_change', 'Price change over 180 days'),
]

# Enable/disable additional fields extraction
EXTRACT_ADDITIONAL_FIELDS = True

# Optional: Allow environment variable override
EXTRACT_ADDITIONAL_FIELDS = os.getenv("EXTRACT_ADDITIONAL_FIELDS", "true").lower() == "true"