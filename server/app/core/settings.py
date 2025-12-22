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
    APP_NAME: str = "AI Avatar API"
    VERSION: str = "1.0"

    # --- Server ---
    FRONTEND_ORIGIN: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

    # --- LOG ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
    LOG_DIR :str= "logs"
    LOG_TO_FILE: bool = bool(os.getenv("LOG_TO_FILE", "False"))
    LOG_MAX_BYTES :int= 10485760
    LOG_BACKUP_COUNT:int = 5

    # --- Database ---
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "rag_chat_db")
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "chroma_db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")

    # --- JWT ---
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # --- Interview ---
    SESSION_DURATION: int = int(os.getenv("SESSION_DURATION", "600"))

    # --- LLM ---
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.8"))
    OLLAMA_TOP_K: int = int(os.getenv("OLLAMA_TOP_K", "40"))
    OLLAMA_TOP_P: float = float(os.getenv("OLLAMA_TOP_P", "0.9"))
    OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
    OLLAMA_SEED: int = int(os.getenv("OLLAMA_SEED", "0"))
    OLLAMA_REPEAT_PENALITY: float = float(os.getenv("OLLAMA_REPEAT_PENALITY", "1.1"))

    # --- TTS ---
    TTS_MODEL: str = os.getenv("TTS_MODEL", "tts_models/en/vctk/vits")
    TTS_SPEAKER: str = os.getenv("TTS_SPEAKER", "p231")

    # --- STT ---
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "medium.en")
    WHISPER_COMPUTE_TYPE: str = "float16" if DEVICE == "cuda" else "int8"
    WHISPER_BEAM_SIZE: int = int(os.getenv("WHISPER_BEAM_SIZE", "3"))

    class Config:
        env_file = ".env"


settings = Settings()
