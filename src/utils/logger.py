import logging
from logging.handlers import RotatingFileHandler
import os
from utils.config_manager import ConfigManager

# Load and validate configuration
config_manager = ConfigManager()
if not config_manager.validate_config():
    raise RuntimeError("Configuration validation failed. Please check your config file and environment variables.")

config = config_manager.config
logging_config = config.get("logging", {})

LOG_FILE = logging_config.get("log_file", "logs/migration.log")
LOG_LEVEL_CONSOLE = logging_config.get("log_level_console", "INFO").upper()
LOG_LEVEL_FILE = logging_config.get("log_level_file", "DEBUG").upper()
MAX_BYTES = logging_config.get("max_bytes", 5_000_000)
BACKUP_COUNT = logging_config.get("backup_count", 5)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S'
    )

    if not logger.handlers:
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, LOG_LEVEL_CONSOLE, logging.INFO))
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File Handler
        fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
        fh.setLevel(getattr(logging, LOG_LEVEL_FILE, logging.DEBUG))
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
