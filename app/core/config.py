from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")

    # LLM provider (default: OpenAI). You can extend later.
    llm_provider: str = Field("openai", alias="LLM_PROVIDER")  # openai | groq | hf
    llm_model: str = Field("gpt-4o-mini", alias="LLM_MODEL")

    # OpenAI
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")

    # Runtime
    log_level: str = Field("INFO", alias="LOG_LEVEL")


settings = Settings()
