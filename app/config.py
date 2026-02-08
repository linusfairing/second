import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dating_app.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    OPENAI_API_KEY: str = ""
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8081","http://localhost:19006"]'
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    @property
    def cors_origins_list(self) -> list[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
