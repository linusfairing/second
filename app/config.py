import json
import secrets

from pydantic_settings import BaseSettings

_INSECURE_DEFAULT = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dating_app.db"
    SECRET_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8081","http://localhost:19006"]'
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    MAX_PASSWORD_LENGTH: int = 72  # bcrypt limit
    REDIS_URL: str = ""  # e.g. "redis://localhost:6379/0"

    @property
    def cors_origins_list(self) -> list[str]:
        try:
            origins = json.loads(self.CORS_ORIGINS)
            if isinstance(origins, list):
                return [str(o) for o in origins]
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# Generate a random key if none provided — safe for dev/test but tokens
# won't survive restarts.  Production should always set SECRET_KEY.
if not settings.SECRET_KEY or settings.SECRET_KEY == _INSECURE_DEFAULT:
    settings.SECRET_KEY = secrets.token_hex(32)
