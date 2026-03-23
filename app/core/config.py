from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Freelance Proposal Analyzer"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Análise técnica avançada de propostas freelance"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/freelance_analyzer"
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
