from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Cyber Fraud Correlator"
    API_PORT: int = 8000
    HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 5173
    DATABASE_URL: str = "sqlite:///./fraud_correlator.db"
    ENCRYPTION_KEY: str | None = None


settings = Settings()
