# app/core/config.py
# Configuration management for Excelly AI Assistant

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # AI Models - Optimized for each functionality
    OPENAI_MODEL: str = "gpt-4o-mini"  # Best for coding and debugging
    GEMINI_PRO_MODEL: str = "gemini-2.0-pro"  # Best for creative and analytical tasks
    GEMINI_FLASH_MODEL: str = "gemini-2.0-flash"  # Best for fast processing and classification
    GEMINI_1_5_PRO_FALLBACK: str = "gemini-1.5-pro"  # Fallback for Pro model
    GEMINI_1_5_FLASH_FALLBACK: str = "gemini-1.5-flash"  # Fallback for Flash model
    
    # Application Settings
    APP_TITLE: str = "Excelly AI Assistant v6.0 (Gemini 2.0)"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: list = [".xlsx", ".xls", ".csv"]
    
    # Session Settings
    SESSION_TIMEOUT: int = 3600  # 1 hour in seconds
    MAX_SESSIONS_PER_USER: int = 10
    
    # AI Request Settings
    AI_REQUEST_TIMEOUT: int = 60  # seconds
    MAX_TOKENS: int = 4000
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./excelly.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        return True

# Global settings instance
settings = Settings()
