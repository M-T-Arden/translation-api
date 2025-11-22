from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Translation API"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/translation_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Optional API Keys
    DEEPL_API_KEY: str = ""
    GOOGLE_TRANSLATE_API_KEY: str = ""
    
    # Encryption
    ENCRYPTION_KEY: str = ""
    
    # Hugging Face token
    HF_TOKEN: str = ""
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()