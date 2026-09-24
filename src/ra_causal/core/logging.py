import logging
import sys

def get_logger(module_id: str = "core") -> logging.Logger:
    logger = logging.getLogger(f"ra_causal.{module_id}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(f"[%(asctime)s] [%(levelname)s] [{module_id}] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

