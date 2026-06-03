"""Centralised logging configuration for CordonNet."""
import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("/var/log/cordonnet")
LOG_FILES = {
    "app":     LOG_DIR / "app.log",
    "hotspot": LOG_DIR / "hotspot.log",
    "clients": LOG_DIR / "clients.log",
}

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure logging for CordonNet.
    File handlers are set up only when /var/log/cordonnet is writable (i.e. root).
    Non-root invocations fall back to console-only logging silently.
    """
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    def _can_write_log_file(path: Path) -> bool:
        """Try opening the actual log file for append — the only reliable check."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a"):
                pass
            return True
        except (PermissionError, OSError):
            return False

    for name, path in LOG_FILES.items():
        logger = logging.getLogger(f"cordonnet.{name}")
        logger.setLevel(level)
        logger.propagate = False
        if _can_write_log_file(path):
            handler = logging.handlers.RotatingFileHandler(
                path, maxBytes=5 * 1024 * 1024, backupCount=3
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        else:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            console.setLevel(logging.WARNING)
            logger.addHandler(console)

    root = logging.getLogger("cordonnet")
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())