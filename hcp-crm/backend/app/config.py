# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     GROQ_API_KEY: str = ""
#     GROQ_PRIMARY_MODEL: str = "gemma2-9b-it"
#     GROQ_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"

#     DATABASE_URL: str = "sqlite:///./hcp_crm.db"
#     FRONTEND_ORIGIN: str = "http://localhost:5173"

#     model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# settings = Settings()

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file (backend/app/config.py -> backend/.env)
# so it loads correctly no matter what directory uvicorn is launched from.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    GROQ_PRIMARY_MODEL: str = "gemma2-9b-it"
    GROQ_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"

    DATABASE_URL: str = "sqlite:///./hcp_crm.db"
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")


settings = Settings()