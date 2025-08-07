# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    API_KEY_PRIVATE_KEY: str
    ACCOUNT_INDEX: str
    API_KEY_INDEX: str

    BASE_URL: str = "https://testnet.zklighter.elliot.ai"

    class Config:
        pass

settings = Settings()
