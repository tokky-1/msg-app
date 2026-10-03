from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Failed logins allowed for one username from one IP before that pair is
    # locked out. Keyed on the pair, not the username alone: a per-username
    # lockout would let anyone lock anyone else out of their account.
    AUTH_MAX_ATTEMPTS: int = 3
    # A single address trying three guesses each against many usernames is
    # still a sweep, so the address has its own ceiling.
    AUTH_MAX_ATTEMPTS_PER_IP: int = 10
    AUTH_LOCKOUT_MINUTES: int = 15

    DB_ECHO: bool = False
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str]
    
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    @property
    def DB_URL(self) -> URL:
        """Built with URL.create, not an f-string.

        A password containing @ : / ? # or % silently produces a wrong or
        unparseable URL when interpolated by hand; URL.create escapes each
        part for us. It also keeps the password out of repr().
        """
        return URL.create(
            "postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()