
# Load environment variables
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

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
