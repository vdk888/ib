
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
