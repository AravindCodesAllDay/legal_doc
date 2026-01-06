import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List
import torch

load_dotenv()


class Settings(BaseSettings):
    """Application-wide environment configuration."""
    # --- Device ---
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

    # --- App ---
    APP_NAME: str = "Docs Handler"
    VERSION: str = "1.0"

    # --- Server ---
    FRONTEND_ORIGIN: List[str] = [
        "http://localhost:5173"
    ]

    # --- LOG ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
    LOG_DIR: str = "logs"
    LOG_TO_FILE: bool = bool(os.getenv("LOG_TO_FILE", "False"))
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5

    # --- Database ---
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "rag_chat_db")
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "chroma_db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")

    # --- LLM ---
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    
    class Config:
        env_file = ".env"


settings = Settings()
