import os
import logging
from logging.handlers import RotatingFileHandler

from app.core.settings import settings


def setup_logging(level: str = settings.LOG_LEVEL):
    """Configure global logging with conditional file handlers, using settings."""

    # Use settings for directory creation and path definitions
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    general_log_dir = os.path.join(settings.LOG_DIR, "system.log")
    user_log_dir = os.path.join(settings.LOG_DIR, "user.log")

    # 1. Basic Configuration for the Root Logger 
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()]
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 2. Conditional File Handler Setup
    if settings.LOG_TO_FILE:
        logger = logging.getLogger()  

        # --- System Log Handler ---
        system_handler = RotatingFileHandler(
            general_log_dir,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        system_handler.setFormatter(formatter)
        logger.addHandler(system_handler)

        # --- User Logger Setup ---
        user_handler = RotatingFileHandler(
            user_log_dir,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        user_handler.setFormatter(formatter)
        user_logger = logging.getLogger("user")
        user_logger.propagate = False
        user_logger.addHandler(user_handler)
        user_logger.setLevel(level)

    # Set uvicorn's log level
    logging.getLogger("uvicorn").setLevel(level)