# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    BYBIT_API_KEY: str
    BYBIT_API_SECRET: str
    TRADINGVIEW_PASSPHRASE: str

    BYBIT_BASE_URL: str = "https://api.bybit.com"
    BYBIT_RECV_WINDOW: int = 5000

    class Config:
        pass

settings = Settings()
