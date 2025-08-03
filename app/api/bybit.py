# app/api/bybit.py
from pybit.unified_trading import HTTP
from app.config import settings

# Initialize the pybit HTTP session.
# The HTTP client automatically handles HMAC-SHA256 signing.
# We will use the mainnet by default, as defined in our config.
bybit_client = HTTP(
    testnet=False, # Set to True for testnet
    api_key=settings.BYBIT_API_KEY,
    api_secret=settings.BYBIT_API_SECRET,
)
