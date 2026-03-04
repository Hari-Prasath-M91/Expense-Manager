import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Expense Manager"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "sqlite:///./expense_manager.db"
    
    # OCR Settings
    TESSERACT_CMD: Optional[str] = None # Will try to auto-detect if None
    
    # Optional LLM Integration for Categorization refinement or cleanups
    GROQ_API_KEY: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
