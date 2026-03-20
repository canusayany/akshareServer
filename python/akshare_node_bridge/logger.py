from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "akshare_node_bridge"
DEFAULT_LOG_FILE = "akshare_server.log"
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 9


def _resolve_log_dir() -> Path:
    configured = os.environ.get("AKSHARE_NODE_LOG_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path.cwd() / "data" / "logs"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / os.environ.get("AKSHARE_NODE_LOG_FILE", DEFAULT_LOG_FILE).strip()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [pid=%(process)d] [%(threadName)s] %(message)s"
    )
    handler.setFormatter(formatter)

    logger.setLevel(getattr(logging, os.environ.get("AKSHARE_NODE_LOG_LEVEL", "INFO").upper(), logging.INFO))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_log_path() -> Path:
    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / os.environ.get("AKSHARE_NODE_LOG_FILE", DEFAULT_LOG_FILE).strip()
