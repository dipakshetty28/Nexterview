from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_origins(value: str) -> list[str]:
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


class Settings(BaseSettings):
    app_name: str = "AI Engineering Interview Platform API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/nexterview"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_request_timeout_seconds: float = 30.0
    frontend_url: str = "http://localhost:3000"
    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_origins: str = ""
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    bcrypt_rounds: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [
            *_split_origins(self.backend_cors_origins),
            *_split_origins(self.cors_origins),
            *_split_origins(self.frontend_url),
        ]
        return list(dict.fromkeys(origins))


settings = Settings()
