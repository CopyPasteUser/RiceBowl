"""Privacy-conscious, bounded diagnostics for a user-owned desktop app."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("macmenu")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    cache_base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    log_path = cache_base / "macmenu" / "macmenu.log"
    try:
        log_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=512 * 1024, backupCount=2, encoding="utf-8")
        os.chmod(log_path, 0o600)
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger
