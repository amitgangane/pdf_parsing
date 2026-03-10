from pydantic_settings import BaseSettings

# Define a Settings class to manage configuration using Pydantic BaseSettings. This allows us to easily load configuration from environment variables or a .env file.
class Settings(BaseSettings):
    openai_api_key: str = ""
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    upload_dir: str = "uploads"
    database_url: str = "postgresql://rag:rag@localhost:5433/rag"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
