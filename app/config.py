# ============================================================================
# Configuration — loads from environment variables
# ============================================================================
# Supports two connection modes:
#   1. DATABASE_URL   (Render auto-injects this)
#   2. Individual vars (POSTGRES_USER, POSTGRES_HOST, etc.)
# ============================================================================
from __future__ import annotations

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file so os.getenv() works locally
load_dotenv()


class Settings(BaseSettings):
    # --- Direct connection params (used by HF Spaces / local Docker) ---------
    postgres_user: str = "expense_admin"
    postgres_password: str = "expense_secure_2026"
    postgres_db: str = "expense_manager"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # --- Full connection string (Render injects this automatically) ----------
    database_url: str | None = None
    cerebras_api_key: str | None = None

    # --- App ----------------------------------------------------------------
    port: int = 10000
    debug: bool = False

    @property
    def asyncpg_dsn(self) -> str:
        """
        Return an asyncpg-compatible DSN.

        Render provides DATABASE_URL as:
            postgres://user:pass@host:port/dbname
        asyncpg expects:
            postgresql://user:pass@host:port/dbname
        """
        if self.database_url:
            url = self.database_url
            # Render uses 'postgres://' but asyncpg needs 'postgresql://'
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url

        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
