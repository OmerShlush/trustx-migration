import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = "logs/migration.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%d-%M-%Y %H:%M:%S'
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger
