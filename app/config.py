from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""

    # App
    app_name: str = "FinanzApp API"
    app_version: str = "1.0.0"
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 5050
    api_prefix: str = "/api/v1"

    # Database
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "finanzapp"
    db_user: str = "postgres"
    db_password: str = "postgres"

    # CORS
    cors_origins: str = "*"

    # File Upload
    upload_dir: str = "uploads"
    max_file_size: int = 10  # MB

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    @property
    def database_url(self) -> str:
        """Generate PostgreSQL database URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
