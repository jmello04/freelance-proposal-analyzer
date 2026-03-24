from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "Freelance Proposal Analyzer"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Análise técnica avançada de propostas freelance"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/freelance_analyzer"

    ANTHROPIC_API_KEY: str = ""
    ANALYSIS_MODEL: str = "claude-sonnet-4-6"
    ANALYSIS_MAX_TOKENS: int = 2048


settings = Settings()
